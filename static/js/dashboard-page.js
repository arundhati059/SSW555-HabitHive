// static/js/dashboard-page.js
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js";
import {
  listActiveHabits, mapTodayProgress, mapProgressLast7,
  createHabit, setHabitDoneToday, lastNDates, setProgressForDays,
  mapProgressByDate, dayKey
} from "./dashboard-data.js";


const auth = window.firebaseAuth;

const form = document.getElementById("add-habit-form");
const inputTitle = document.getElementById("habit-title");
const inputMarkToday = document.getElementById("habit-mark-today");
const list = document.getElementById("habit-list");
const emptyBox = document.getElementById("empty-state");

// 整體進度條
const pWrap = document.getElementById("progress-wrap");
const pText = document.getElementById("progress-text");
const pCount = document.getElementById("progress-count");
const pBar  = document.getElementById("progress-bar");

// 🔁 View switching
const viewSwitch   = document.getElementById("habit-view-switch");
const viewList     = document.getElementById("habit-view-list");
const viewHistory  = document.getElementById("habit-view-history");
const viewCalendar = document.getElementById("habit-view-calendar");

// 📜 Weekly history list
const historyList = document.getElementById("history-list");

// 📅 Calendar view
const calendarGrid  = document.getElementById("calendar-grid");
const calendarLabel = document.getElementById("calendar-label");
const calendarPrev  = document.getElementById("calendar-prev");
const calendarNext  = document.getElementById("calendar-next");
const calendarDetail = document.getElementById("calendar-detail");

// Cache & state
let cachedProgressByDate = {};
let cachedHabits = [];
let calendarYear = null;
let calendarMonth = null;

// 🔁 切換 List / Weekly / Monthly 視圖
if (viewSwitch) {
  viewSwitch.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-view]");
    if (!btn) return;
    const view = btn.getAttribute("data-view");

    // active 樣式
    viewSwitch.querySelectorAll("button").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    // 顯示/隱藏各視圖
    if (viewList)     viewList.style.display     = (view === "list"     ? "" : "none");
    if (viewHistory)  viewHistory.style.display  = (view === "history"  ? "" : "none");
    if (viewCalendar) viewCalendar.style.display = (view === "calendar" ? "" : "none");
  });
}


// 產生 7 格（今天在最左），daysMap: {'YYYY-MM-DD': true}
function habitInteractiveBar(habitId, daysMap, onCommit) {
  const container = document.createElement("div");
  // 用自己的 class，不再依賴 bootstrap 的 d-flex
  container.className = "habit-week-bar";
  const dates = lastNDates(7); // [today, yesterday,...]

  // 拖拉狀態
  let isDragging = false;
  let paintTo = null; // true(塗成完成) or false(塗成未完成)
  const pending = {}; // 暫存這次拖拉的變更 {'YYYY-MM-DD': bool}

  function cellEl(dateKey, completed) {
    const el = document.createElement("div");
    el.dataset.date = dateKey;
    el.title = dateKey;
    el.className = "habit-week-cell" + (completed ? " completed" : "");

    const refresh = (v) => {
      if (v) el.classList.add("completed");
      else el.classList.remove("completed");
    };

    const setTemp = (v) => {
      pending[dateKey] = v;
      refresh(v);
    };

    el.addEventListener("mousedown", (e) => {
      e.preventDefault();
      isDragging = true;
      // 第一個被點的格子：決定這次塗抹目標狀態（反轉）
      const current = !!daysMap[dateKey];
      paintTo = !current;
      setTemp(paintTo);
    });

    el.addEventListener("mouseenter", () => {
      if (!isDragging || paintTo === null) return;
      setTemp(paintTo);
    });

    // 支援點一下（無拖拉）
    el.addEventListener("click", async (e) => {
      if (isDragging) return; // 交給 mouseup 處理
      const next = !daysMap[dateKey];
      pending[dateKey] = next;
      refresh(next);
      await onCommit({ ...pending });
      // 清空暫存
      for (const k in pending) delete pending[k];
    });

    return el;
  }

  dates.forEach((dk) => {
    container.appendChild(cellEl(dk, !!daysMap[dk]));
  });

  // 完成拖拉
  window.addEventListener("mouseup", async () => {
    if (!isDragging) return;
    isDragging = false;
    if (paintTo === null) return;
    await onCommit({ ...pending });
    // 清空暫存
    for (const k in pending) delete pending[k];
    paintTo = null;
  });

  return container;
}

async function render(uid) {
  list.innerHTML = "";
  emptyBox.style.display = "none";
  if (pWrap) pWrap.style.display = "none";

  let habits = [], todayMap = {}, last7Map = {}, progressByDate = {};

  try {
    [habits, todayMap, last7Map, progressByDate] = await Promise.all([
      listActiveHabits(uid),
      mapTodayProgress(uid),
      mapProgressLast7(uid),
      mapProgressByDate(uid),   // 🔍 所有日期的完成紀錄
    ]);
  } catch (e) {
    console.error("[dashboard] load error", e);
    alert("Load failed: " + (e?.message || e));
    return;
  }

  // Cache for other views
  cachedHabits = habits;
  cachedProgressByDate = progressByDate;

  // 整體 Today 進度
  const total = habits.length;
  const completedToday = habits.filter(h => !!todayMap[h.id]).length;
  const percent = total ? Math.round((completedToday / total) * 100) : 0;

  if (pWrap) {
    pWrap.style.display = "block";
    pText.textContent = `Today: ${percent}% completed`;
    pCount.textContent = `${completedToday} / ${total}`;
    pBar.style.width = `${percent}%`;
    pBar.setAttribute("aria-valuenow", String(percent));
  }

  // ⭐ User Story 1 其中一部份：沒有 habit 時顯示 empty state
  if (habits.length === 0) {
    emptyBox.style.display = "block";
    // history + calendar 清空一下
    if (historyList) historyList.innerHTML = "";
    if (calendarGrid) calendarGrid.innerHTML = "";
    if (calendarDetail) calendarDetail.textContent = "";
    return;
  }

  // 📋 List 視圖：列出所有 active habits + 今天/7天完成狀態
  habits.forEach(h => {
    const meta = last7Map[h.id] || { count: 0, days: {} };
    const done7 = meta.count || 0;
    const doneToday = !!todayMap[h.id];

    const li = document.createElement("li");
    li.className = "list-group-item";
    li.innerHTML = `
      <div class="d-flex align-items-center justify-content-between">
        <div class="flex-grow-1 pe-3">
          <strong>${h.title}</strong>
          <div class="text-muted" style="font-size:12px;">
            ${doneToday ? "Today: done ✅" : "Today: not done"}
          </div>
          <div class="text-muted" style="font-size:12px;">
            ${done7}/7 last days ${done7 === 7 ? " 🎉" : ""}
          </div>
        </div>
        <button class="btn btn-sm ${doneToday ? "btn-outline-secondary" : "btn-success"}">
          ${doneToday ? "Unmark today" : "Mark today"}
        </button>
      </div>
    `;

    // 7 格拖拉條
    const barHost = document.createElement("div");
    barHost.className = "mt-2";
    const daysMap = meta.days || {};
    const interactive = habitInteractiveBar(h.id, daysMap, async (changes) => {
      try {
        await setProgressForDays(uid, h.id, changes);
        await render(uid);
      } catch (e) {
        console.error("[dashboard] drag commit error", e);
        alert("Update failed: " + (e?.message || e));
      }
    });
    barHost.appendChild(interactive);
    li.querySelector(".flex-grow-1").appendChild(barHost);

    // 今天快捷鍵
    const btn = li.querySelector("button");
    btn.addEventListener("click", async () => {
      try {
        await setHabitDoneToday(uid, h.id, !doneToday);
        await render(uid);
      } catch (e) {
        console.error("[dashboard] mark today error", e);
        alert("Mark failed: " + (e?.message || e));
      }
    });

    list.appendChild(li);
  });

  // 📜 User Story 1：每日歷史清單（最近 7 天）
  renderHistory(habits, last7Map);

  // 📅 User Story 2：月曆視圖（含 daily 點擊詳情）
  if (calendarYear === null || calendarMonth === null) {
    const today = new Date();
    calendarYear = today.getFullYear();
    calendarMonth = today.getMonth(); // 0-based
  }
  renderCalendar(progressByDate);
}

// 📜 Weekly history list：用 last7Map + habits 組成「每天」的清單
function renderHistory(habits, last7Map) {
  if (!historyList) return;

  const days = lastNDates(7); // [today, yesterday, ...]
  const habitNameById = {};
  habits.forEach(h => {
    habitNameById[h.id] = h.title || "Untitled habit";
  });

  // 反轉成「以日期為 key」：{ dateKey: [habitName...] }
  const byDate = {};
  Object.entries(last7Map).forEach(([habitId, meta]) => {
    if (!meta.days) return;
    const name = habitNameById[habitId] || "Untitled habit";
    Object.keys(meta.days).forEach(dateKey => {
      if (!byDate[dateKey]) byDate[dateKey] = [];
      byDate[dateKey].push(name);
    });
  });

  const total = habits.length;
  const itemsHtml = days.map(dateKey => {
    const completed = byDate[dateKey] || [];
    const count = completed.length;
    const percent = total ? Math.round((count / total) * 100) : 0;

    // 格式化日期，例如 "Mon, Nov 17"
    const displayDate = new Date(dateKey + "T00:00:00").toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      weekday: "short",
    });

    const habitBadges = completed.length
      ? completed.map(name => `<span class="badge bg-success me-1 mb-1">${name}</span>`).join("")
      : `<span class="text-muted">No habits completed</span>`;

    return `
      <div class="list-group-item">
        <div class="d-flex justify-content-between align-items-start">
          <div>
            <strong>${displayDate}</strong>
            <div class="small text-muted">
              ${count} / ${total} habits done (${percent}%)
            </div>
          </div>
          <div class="text-end" style="max-width: 60%;">
            ${habitBadges}
          </div>
        </div>
      </div>
    `;
  }).join("");

  historyList.innerHTML = itemsHtml;
}

function renderCalendar(progressByDate) {
  if (!calendarGrid || calendarYear === null || calendarMonth === null) return;

  const year = calendarYear;
  const month = calendarMonth; // 0-11

  const firstDay = new Date(year, month, 1);
  const startWeekday = firstDay.getDay(); // 0(Sun) - 6(Sat)
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const todayKey = dayKey(); // 'YYYY-MM-DD' of today

  const monthNames = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
  ];
  const weekdayNames = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

  if (calendarLabel) {
    calendarLabel.textContent = `${monthNames[month]} ${year}`;
  }

  // header row
  let html = `<div class="d-flex mb-1 calendar-header">` +
    weekdayNames.map(w => `<div class="flex-fill text-center fw-bold small">${w}</div>`).join("") +
    `</div>`;

  const totalCells = startWeekday + daysInMonth;
  const weeks = Math.ceil(totalCells / 7);

  let day = 1;

  for (let w = 0; w < weeks; w++) {
    html += `<div class="d-flex mb-1 calendar-row">`;

    for (let d = 0; d < 7; d++) {
      const cellIndex = w * 7 + d;

      if (cellIndex < startWeekday || day > daysInMonth) {
        html += `<div class="flex-fill calendar-cell empty"></div>`;
      } else {
        const dateObj = new Date(year, month, day);
        const dateKey = dayKey(dateObj);
        const summary = progressByDate[dateKey];
        const count = summary ? summary.count : 0;

        const classes = ["calendar-cell", "flex-fill", "border", "p-1", "text-center"];
        if (count > 0) classes.push("has-completion");
        if (dateKey === todayKey) classes.push("today");

        html += `
          <div class="${classes.join(" ")}" data-date="${dateKey}">
            <div class="calendar-day-number fw-bold">${day}</div>
            <div class="calendar-day-count small text-muted">
              ${count > 0 ? `${count} done` : ""}
            </div>
          </div>
        `;
        day++;
      }
    }

    html += `</div>`;
  }

  calendarGrid.innerHTML = html;

  // 點某一天 -> daily 詳細
  const cells = calendarGrid.querySelectorAll(".calendar-cell[data-date]");
  cells.forEach(cell => {
    cell.addEventListener("click", () => {
      const dateKey = cell.dataset.date;
      renderCalendarDetail(dateKey, progressByDate);
    });
  });
}

function renderCalendarDetail(dateKey, progressByDate) {
  if (!calendarDetail) return;

  const summary = progressByDate[dateKey];
  const dateObj = new Date(dateKey + "T00:00:00");
  const displayDate = dateObj.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    weekday: "long",
  });

  if (!summary) {
    calendarDetail.innerHTML = `
      <strong>${displayDate}</strong>
      <div class="mt-1">No habits completed on this day.</div>
    `;
    return;
  }

  const habitNameById = {};
  cachedHabits.forEach(h => {
    habitNameById[h.id] = h.title || "Untitled habit";
  });

  const names = (summary.habitIds || []).map(
    id => habitNameById[id] || "Unknown habit"
  );

  const chips = names.map(
    name => `<span class="badge bg-success me-1 mb-1">${name}</span>`
  ).join("");

  calendarDetail.innerHTML = `
    <strong>${displayDate}</strong>
    <div class="mt-1">
      ${chips || "No habits completed on this day."}
    </div>
  `;
}


// 新增 Habit
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = (inputTitle.value || "").trim();
    if (!title) return alert("Please enter a habit title");
    const u = auth.currentUser;
    if (!u) return alert("Please sign in first");

    try {
      await createHabit(u.uid, { title, markTodayDone: inputMarkToday.checked });
    } catch (err) {
      console.error("[dashboard] create error", err);
      alert("Create failed: " + (err?.message || err));
      return;
    }
    inputTitle.value = "";
    inputMarkToday.checked = true;
    await render(u.uid);
  });
}

// 初始載入/登入狀態更新
onAuthStateChanged(auth, (u) => {
  if (u) render(u.uid);
  else {
    list.innerHTML = "";
    emptyBox.style.display = "block";
    if (pWrap) pWrap.style.display = "none";
    if (historyList) historyList.innerHTML = "";
    if (calendarGrid) calendarGrid.innerHTML = "";
    if (calendarDetail) calendarDetail.textContent = "";
  }
});


if (calendarPrev) {
  calendarPrev.addEventListener("click", () => {
    if (calendarYear === null || calendarMonth === null) return;
    calendarMonth -= 1;
    if (calendarMonth < 0) {
      calendarMonth = 11;
      calendarYear -= 1;
    }
    renderCalendar(cachedProgressByDate);
  });
}

if (calendarNext) {
  calendarNext.addEventListener("click", () => {
    if (calendarYear === null || calendarMonth === null) return;
    calendarMonth += 1;
    if (calendarMonth > 11) {
      calendarMonth = 0;
      calendarYear += 1;
    }
    renderCalendar(cachedProgressByDate);
  });
}


