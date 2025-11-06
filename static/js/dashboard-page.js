// static/js/dashboard-page.js
import {
  listActiveHabits, mapTodayProgress, mapProgressLast7,
  createHabit, setHabitDoneToday, deleteHabit, updateHabit, lastNDates, setProgressForDays
} from "./dashboard-data.js";

const form = document.getElementById("add-habit-form");
const inputTitle = document.getElementById("habit-title");
const inputDescription = document.getElementById("habit-description");
const inputCategory = document.getElementById("habit-category");
const inputPrivacy = document.getElementById("habit-privacy");
const inputMarkToday = document.getElementById("habit-mark-today");
const list = document.getElementById("habit-list");
const emptyBox = document.getElementById("empty-state");

const pWrap = document.getElementById("progress-wrap");
const pText = document.getElementById("progress-text");
const pCount = document.getElementById("progress-count");
const pBar = document.getElementById("progress-bar");

let editModal;
let currentEditingHabit = null;

function getTodayFormatted() {
  const today = new Date();
  const options = { month: 'short', day: 'numeric', year: 'numeric' };
  return today.toLocaleDateString('en-US', options);
}

function getCategoryEmoji(category) {
  const emojiMap = {
    'General': '📁',
    'Health': '💪',
    'Fitness': '🏃',
    'Productivity': '⚡',
    'Learning': '📚',
    'Mindfulness': '🧘',
    'Social': '👥',
    'Finance': '💰',
    'Hobbies': '🎨'
  };
  return emojiMap[category] || '📁';
}

function getPrivacyIcon(privacy) {
  const iconMap = {
    'public': '🌍',
    'friends': '👥',
    'private': '🔒'
  };
  return iconMap[privacy] || '🌍';
}

document.addEventListener('DOMContentLoaded', () => {
  const modalElement = document.getElementById('editHabitModal');
  editModal = new bootstrap.Modal(modalElement);
  
  document.getElementById('save-habit-btn').addEventListener('click', async () => {
    if (!currentEditingHabit) return;
    
    const newDescription = document.getElementById('edit-habit-description').value.trim();
    const newCategory = document.getElementById('edit-habit-category').value;
    const newPrivacy = document.getElementById('edit-habit-privacy').value;
    
    try {
      await updateHabit(currentEditingHabit, { 
        description: newDescription,
        category: newCategory,
        privacy: newPrivacy
      });
      editModal.hide();
      await render();
    } catch (e) {
      console.error("[dashboard] update error", e);
      alert("Update failed: " + (e?.message || e));
    }
  });
  
  render();
});

function openEditModal(habit) {
  currentEditingHabit = habit.name;
  document.getElementById('edit-habit-name').value = habit.name;
  document.getElementById('edit-habit-description').value = habit.description || '';
  document.getElementById('edit-habit-category').value = habit.category || 'General';
  document.getElementById('edit-habit-privacy').value = habit.privacy || 'public';
  editModal.show();
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
    const categoryEmoji = getCategoryEmoji(h.category || 'General');
    const privacyIcon = getPrivacyIcon(h.privacy || 'public');

    const li = document.createElement("li");
    li.className = "list-group-item habit-list-item";
    
    const descriptionHTML = h.description && h.description.trim() 
      ? `<div class="text-muted habit-description" style="font-size:12px; margin-top: 4px;">${h.description}</div>` 
      : '<div class="text-muted habit-description" style="font-size:11px; margin-top: 4px; font-style: italic; color: #999;">Click to add details...</div>';
    
    const categoryBadge = `<span class="badge bg-secondary" style="font-size:10px; margin-left: 8px;">${categoryEmoji} ${h.category || 'General'}</span>`;
    const privacyBadge = `<span class="badge bg-info" style="font-size:10px; margin-left: 4px;" title="${h.privacy || 'public'}">${privacyIcon}</span>`;
    
    li.innerHTML = `
      <div class="d-flex align-items-center justify-content-between">
        <div class="flex-grow-1 pe-3 habit-clickable" style="cursor: pointer;">
          <div>
            <strong class="habit-name">${h.name}</strong>
            ${categoryBadge}
            ${privacyBadge}
          </div>
          ${descriptionHTML}
          <div class="text-muted" style="font-size:12px; margin-top: 4px;">
            ${todayDate}: ${doneToday ? "<strong>Finished ✅</strong>" : "not finished"}
          </div>
        </div>
        <div class="d-flex gap-2">
          <button class="btn btn-sm ${doneToday ? "btn-outline-secondary" : "btn-success"} mark-btn">
            ${doneToday ? "Unmark" : "Mark"}
          </button>
          <button class="btn btn-sm btn-outline-danger delete-btn" title="Delete habit">
            🗑️
          </button>
        </div>
      </div>
    `;

    const clickableArea = li.querySelector(".habit-clickable");
    clickableArea.addEventListener("click", () => {
      openEditModal(h);
    });

    const markBtn = li.querySelector(".mark-btn");
    markBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        await setHabitDoneToday(h.name, !doneToday);
        await render();
      } catch (e) {
        console.error("[dashboard] mark today error", e);
        alert("Mark failed: " + (e?.message || e));
      }
    });

    const deleteBtn = li.querySelector(".delete-btn");
    deleteBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (confirm(`Are you sure you want to delete "${h.name}"?`)) {
        try {
          await deleteHabit(h.name);
          await render();
        } catch (e) {
          console.error("[dashboard] delete error", e);
          alert("Delete failed: " + (e?.message || e));
        }
      }
    });

    list.appendChild(li);
  });
}

if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = (inputTitle.value || "").trim();
    const description = (inputDescription.value || "").trim();
    const category = inputCategory.value;
    const privacy = inputPrivacy.value;
    
    if (!title) return alert("Please enter a habit title");

    try {
      await createHabit({ 
        name: title,
        description: description,
        category: category,
        privacy: privacy,
        markTodayDone: inputMarkToday.checked 
      });
    } catch (err) {
      console.error("[dashboard] create error", err);
      alert("Create failed: " + (err?.message || err));
      return;
    }
    
    inputTitle.value = "";
    inputDescription.value = "";
    inputCategory.value = "General";
    inputPrivacy.value = "public";
    inputMarkToday.checked = true;
    await render();
  });
}
