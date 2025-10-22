
async function loadHabits() {
    const res = await fetch("/habits");
    const habits = await res.json();
    const container = document.getElementById("habits");
    container.innerHTML = "";
    habits.forEach(habit => {
        const div = document.createElement("div");
        div.className = "habit" + (habit.completed ? " completed" : "");
        div.innerHTML = `${habit.name} <button onclick="toggleHabit(${habit.id})">Toggle</button>`;
        container.appendChild(div);
    });
}

async function toggleHabit(id) {
    await fetch(`/habits/${id}/toggle`, { method: "POST" });
    loadHabits();
}

loadHabits();
alert("script1.js loaded!");
