document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("habitForm");
    if (!form) return;
  
    const errorBox = document.getElementById("habitError");
    const successBox = document.getElementById("habitSuccess");
    const submitBtn = document.getElementById("habitSubmit");
  
    const show = (el, msg, cls) => {
      el.textContent = msg;
      el.classList.remove("d-none", "alert-danger", "alert-success");
      el.classList.add(cls);
    };
  
    const hide = (el) => el.classList.add("d-none");
  
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      hide(errorBox);
      hide(successBox);
  
      const payload = {
        name: document.getElementById("habitName").value.trim(),
        description: document.getElementById("habitPurpose").value.trim(),
        frequency: document.getElementById("habitFrequency").value,
        reminderTime: document.getElementById("habitTime").value,
        reminderEnabled: document.getElementById("reminderEnabled").checked,
      };
  
      if (!payload.name || !payload.description) {
        show(errorBox, "Please fill all required fields.", "alert-danger");
        return;
      }
  
      submitBtn.disabled = true;
      submitBtn.textContent = "Creating...";
  
      try {
        const res = await fetch("/api/habits", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(payload),
        });
  
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          show(errorBox, data.error || "Server error while creating habit.", "alert-danger");
        } else {
          show(successBox, "Habit created successfully!", "alert-success");
          form.reset();
        }
      } catch (err) {
        console.error("Network error:", err);
        show(errorBox, "Network error — Flask may not be running on 127.0.0.1:5000.", "alert-danger");
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Create Habit";
      }
    });
  });
  