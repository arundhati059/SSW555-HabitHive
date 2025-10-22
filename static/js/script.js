// Function to render a single habit
function addHabitToDOM(habit) {
    const habitsDiv = document.getElementById("habits");
    const habitDiv = document.createElement("div");
    habitDiv.className = "habit";

    const habitSpan = document.createElement("span");
    habitSpan.textContent = `${habit.name} (${habit.category || "No category"})`;
    if (habit.completed) {
        habitSpan.classList.add("completed");
    }

    const toggleButton = document.createElement("button");
    toggleButton.textContent = "Toggle";
    toggleButton.onclick = async () => {
        const response = await fetch(`/habits/${habit.id}/toggle`, { method: "POST" });
        const updatedHabit = await response.json();
        // Update the completed style
        habitSpan.classList.toggle("completed", updatedHabit.completed);
    };

    habitDiv.appendChild(habitSpan);
    habitDiv.appendChild(toggleButton);
    habitsDiv.appendChild(habitDiv);
}

// Handle form submission
document.getElementById("addHabitForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("habitName").value;
    const category = document.getElementById("habitCategory").value;

    const response = await fetch("/habits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, category })
    });

    const newHabit = await response.json();
    addHabitToDOM(newHabit); // Add the new habit to the page
    document.getElementById("habitName").value = "";
    document.getElementById("habitCategory").value = "";
});

alert("script.js loaded!");
