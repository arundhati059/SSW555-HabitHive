// static/js/dashboard-page.js
import {
  listActiveHabits, mapTodayProgress, mapProgressLast7,
  createHabit, setHabitDoneToday, lastNDates, setProgressForDays
} from "./dashboard-data.js";

const form = document.getElementById("add-habit-form");
const inputTitle = document.getElementById("habit-title");
const inputMarkToday = document.getElementById("habit-mark-today");
const list = document.getElementById("habit-list");
const emptyBox = document.getElementById("empty-state");

// Overall progress bar
const pWrap = document.getElementById("progress-wrap");
const pText = document.getElementById("progress-text");
const pCount = document.getElementById("progress-count");
const pBar = document.getElementById("progress-bar");

// Helper function to format today's date
function getTodayFormatted() {
  const today = new Date();
  const options = { month: 'short', day: 'numeric', year: 'numeric' };
  return today.toLocaleDateString('en-US', options);
  // Returns format like: "Nov 5, 2025"
}

async function render() {
  list.innerHTML = "";
  emptyBox.style.display = "none";
  if (pWrap) pWrap.style.display = "none";

  let habits = [], todayMap = {}, last7Map = {};
  try {
    [habits, todayMap, last7Map] = await Promise.all([
      listActiveHabits(),
      mapTodayProgress(),
      mapProgressLast7(),
    ]);
  } catch (e) {
    console.error("[dashboard] load error", e);
    alert("Load failed: " + (e?.message || e));
    return;
  }

  // Overall today's progress
  const total = habits.length;
  const completedToday = habits.filter(h => !!todayMap[h.name]).length;
  const percent = total ? Math.round((completedToday / total) * 100) : 0;
  const todayDate = getTodayFormatted();

  if (pWrap) {
    pWrap.style.display = "block";
    pText.textContent = `${todayDate}: ${percent}% completed`;
    pCount.textContent = `${completedToday} / ${total}`;
    pBar.style.width = `${percent}%`;
    pBar.setAttribute("aria-valuenow", String(percent));
  }

  // Only show habits that haven't been completed all 7 days
  const pending = habits.filter(h => {
    const c = last7Map[h.name]?.count ?? 0;
    return c < 7;
  });

  if (pending.length === 0) {
    emptyBox.style.display = "block";
    return;
  }

  pending.forEach(h => {
    const doneToday = !!todayMap[h.name];

    const li = document.createElement("li");
    li.className = "list-group-item";
    li.innerHTML = `
      <div class="d-flex align-items-center justify-content-between">
        <div class="flex-grow-1 pe-3">
          <strong>${h.name}</strong>
          ${h.description ? `<div class="text-muted" style="font-size:11px;">${h.description}</div>` : ''}
          <div class="text-muted" style="font-size:12px;">
            ${todayDate}: ${doneToday ? "done ✅" : "not done"}
          </div>
        </div>
        <button class="btn btn-sm ${doneToday ? "btn-outline-secondary" : "btn-success"}">
          ${doneToday ? "Unmark today" : "Mark today"}
        </button>
      </div>
    `;

    // Toggle today's completion
    const btn = li.querySelector("button");
    btn.addEventListener("click", async () => {
      try {
        await setHabitDoneToday(h.name, !doneToday);
        await render();
      } catch (e) {
        console.error("[dashboard] mark today error", e);
        alert("Mark failed: " + (e?.message || e));
      }
    });

    list.appendChild(li);
  });
}

// Add new habit
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = (inputTitle.value || "").trim();
    if (!title) return alert("Please enter a habit title");

    try {
      await createHabit({ 
        name: title, 
        markTodayDone: inputMarkToday.checked 
      });
    } catch (err) {
      console.error("[dashboard] create error", err);
      alert("Create failed: " + (err?.message || err));
      return;
    }
    inputTitle.value = "";
    inputMarkToday.checked = true;
    await render();
  });
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
  render();
});
