// static/js/dashboard-data.js

export function dayKey(d = new Date()) {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export function lastNDates(n = 7) {
  const days = [];
  const base = new Date();
  for (let i = 0; i < n; i++) {
    const d = new Date(base);
    d.setDate(base.getDate() - i);
    days.push(dayKey(d));
  }
  return days;
}

export async function listActiveHabits() {
  try {
    const response = await fetch('/habits', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || 'Failed to load habits');
    }
    
    const active = data.habits.filter(h => h.is_active !== false);
    active.sort((a, b) => {
      const dateA = new Date(a.created_at || 0);
      const dateB = new Date(b.created_at || 0);
      return dateB - dateA;
    });
    
    return active;
  } catch (error) {
    console.error('Error loading habits:', error);
    throw error;
  }
}

export async function mapTodayProgress() {
  try {
    const habits = await listActiveHabits();
    const today = dayKey();
    const map = {};
    
    habits.forEach(habit => {
      const completionHistory = habit.completion_history || [];
      if (completionHistory.includes(today)) {
        map[habit.name] = true;
      }
    });
    
    return map;
  } catch (error) {
    console.error('Error loading today progress:', error);
    throw error;
  }
}

export async function mapProgressLast7() {
  try {
    const habits = await listActiveHabits();
    const days = new Set(lastNDates(7));
    const byHabit = {};
    
    habits.forEach(habit => {
      const completionHistory = habit.completion_history || [];
      const daysMap = {};
      let count = 0;
      
      completionHistory.forEach(date => {
        if (days.has(date)) {
          daysMap[date] = true;
          count++;
        }
      });
      
      byHabit[habit.name] = { count, days: daysMap };
    });
    
    return byHabit;
  } catch (error) {
    console.error('Error loading last 7 days progress:', error);
    throw error;
  }
}

// KEEP ONLY THIS ONE - with privacy parameter
export async function createHabit({ name, description = '', category = 'General', privacy = 'public', markTodayDone = false }) {
  try {
    const response = await fetch('/habits/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: name,
        description: description,
        frequency: 'daily',
        target_count: 1,
        category: category,
        privacy: privacy
      }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || 'Failed to create habit');
    }
    
    if (markTodayDone) {
      await setHabitDoneToday(name, true);
    }
    
    return name;
  } catch (error) {
    console.error('Error creating habit:', error);
    throw error;
  }
}

export async function setHabitDoneToday(habitName, markComplete) {
  try {
    if (markComplete) {
      const response = await fetch(`/habits/${encodeURIComponent(habitName)}/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (!data.success) {
        throw new Error(data.error || 'Failed to mark habit complete');
      }
    } else {
      const response = await fetch(`/habits/${encodeURIComponent(habitName)}/uncomplete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (!data.success) {
        throw new Error(data.error || 'Failed to unmark habit');
      }
    }
  } catch (error) {
    console.error('Error updating habit completion:', error);
    throw error;
  }
}

export async function deleteHabit(habitName) {
  try {
    const response = await fetch(`/habits/${encodeURIComponent(habitName)}/delete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || 'Failed to delete habit');
    }
    
    return true;
  } catch (error) {
    console.error('Error deleting habit:', error);
    throw error;
  }
}

export async function updateHabit(habitName, updates) {
  try {
    const response = await fetch(`/habits/${encodeURIComponent(habitName)}/update`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || 'Failed to update habit');
    }
    
    return true;
  } catch (error) {
    console.error('Error updating habit:', error);
    throw error;
  }
}

export async function setProgressForDays(habitName, datesToState) {
  const today = dayKey();
  const entries = Object.entries(datesToState);
  
  for (const [date, completed] of entries) {
    const last7 = new Set(lastNDates(7));
    if (!last7.has(date)) continue;
    
    if (date === today) {
      await setHabitDoneToday(habitName, completed);
    } else {
      console.warn(`Updating past date ${date} not yet implemented`);
    }
  }
}
