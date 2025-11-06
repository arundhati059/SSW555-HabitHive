// static/js/dashboard-page.js
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js";
import {
  listActiveHabits, mapTodayProgress, mapProgressLast7,
  createHabit, setHabitDoneToday, lastNDates, setProgressForDays
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

// 產生 7 格（今天在最左），daysMap: {'YYYY-MM-DD': true}
function habitInteractiveBar(habitId, daysMap, onCommit) {
  const container = document.createElement("div");
  container.className = "d-flex gap-1 mt-2 align-items-center";
  const dates = lastNDates(7); // [today, yesterday,...]

  // 拖拉狀態
  let isDragging = false;
  let paintTo = null; // true(塗成完成) or false(塗成未完成)
  const pending = {}; // 暫存這次拖拉的變更 {'YYYY-MM-DD': bool}

  function cellEl(dateKey, completed) {
    const el = document.createElement("div");
    el.dataset.date = dateKey;
    el.title = dateKey;
    el.style.width = "20px";
    el.style.height = "14px";
    el.style.borderRadius = "4px";
    el.style.border = "1px solid rgba(0,0,0,0.15)";
    el.style.cursor = "pointer";
    el.style.background = completed ? "var(--bs-success)" : "rgba(0,0,0,0.05)";

    const refresh = (v) => {
      el.style.background = v ? "var(--bs-success)" : "rgba(0,0,0,0.05)";
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
      await onCommit(pending);
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
    await onCommit(pending);
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

  let habits = [], todayMap = {}, last7Map = {};
  try {
    [habits, todayMap, last7Map] = await Promise.all([
      listActiveHabits(uid),
      mapTodayProgress(uid),
      mapProgressLast7(uid),
    ]);
  } catch (e) {
    console.error("[dashboard] load error", e);
    alert("Load failed: " + (e?.message || e));
    return;
  }

  // 頁面頂部的「今天整體進度」維持原本邏輯
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

  // ⭐ 新邏輯：只有「最近 7 天全滿（7/7）」的才從清單消失
  const pending = habits.filter(h => {
    const c = last7Map[h.id]?.count ?? 0;
    return c < 7; // 7/7 就不顯示；其餘都顯示
  });

  if (pending.length === 0) {
    emptyBox.style.display = "block";
    return;
  }

  pending.forEach(h => {
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
          <div class="text-muted" style="font-size:12px;">${done7}/7 last days</div>
        </div>
        <button class="btn btn-sm ${doneToday ? "btn-outline-secondary" : "btn-success"}">
          ${doneToday ? "Unmark today" : "Mark today"}
        </button>
      </div>
    `;

    // 7 格拖拉條（沿用你現有的互動條建立方式）
    const barHost = document.createElement("div");
    barHost.className = "mt-2";
    const daysMap = meta.days || {};
    const interactive = habitInteractiveBar(h.id, daysMap, async (changes) => {
      try {
        await setProgressForDays(uid, h.id, changes);
        await render(uid); // 更新：若達到 7/7 就會從清單消失
      } catch (e) {
        console.error("[dashboard] drag commit error", e);
        alert("Update failed: " + (e?.message || e));
      }
    });
    barHost.appendChild(interactive);
    li.querySelector(".flex-grow-1").appendChild(barHost);

    // 今天快捷鍵：按一下切換今天完成/取消
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
  }
});

