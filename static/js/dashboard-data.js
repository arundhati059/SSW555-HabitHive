// static/js/dashboard-data.js
import {
  getFirestore, collection, addDoc, doc, deleteDoc, getDocs,
  query, where, serverTimestamp, limit
} from "https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js";

const db = getFirestore(window.firebaseAuth.app);

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
  return days; // [today, yesterday, ...]
}

// 只用 userID（其餘在前端過濾/排序，避免索引）
export async function listActiveHabits(uid) {
  const qh = query(collection(db, "habits"), where("userID", "==", uid));
  const snap = await getDocs(qh);
  const all = snap.docs.map(d => ({ id: d.id, ...d.data() }));
  const active = all.filter(h => h.active !== false);
  active.sort((a, b) => (b.createdAt?.seconds ?? 0) - (a.createdAt?.seconds ?? 0));
  return active;
}

// 今天完成 map（只以 userID 查，回來過濾今天）
export async function mapTodayProgress(uid) {
  const today = dayKey();
  const qp = query(collection(db, "progress"), where("userID", "==", uid));
  const snap = await getDocs(qp);
  const m = {};
  snap.forEach(d => {
    const data = d.data();
    if (data.date === today && data.habitId) m[data.habitId] = d.id;
  });
  return m;
}

// 最近 7 天每個 habit 的完成日集合與次數
export async function mapProgressLast7(uid) {
  const days = new Set(lastNDates(7));
  const qp = query(collection(db, "progress"), where("userID", "==", uid));
  const snap = await getDocs(qp);

  const byHabit = {}; // { habitId: { count, days: { 'YYYY-MM-DD': true } } }
  snap.forEach(docSnap => {
    const p = docSnap.data();
    if (!p.habitId || !p.date) return;
    if (!days.has(p.date)) return;
    if (!byHabit[p.habitId]) byHabit[p.habitId] = { count: 0, days: {} };
    if (!byHabit[p.habitId].days[p.date]) {
      byHabit[p.habitId].days[p.date] = true;
      byHabit[p.habitId].count += 1;
    }
  });

  return byHabit;
}

export async function createHabit(uid, { title, markTodayDone }) {
  const ref = await addDoc(collection(db, "habits"), {
    userID: uid,
    title,
    schedule: "daily",
    active: true,
    createdAt: serverTimestamp(),
  });
  if (markTodayDone) {
    await addDoc(collection(db, "progress"), {
      userID: uid,
      habitId: ref.id,
      date: dayKey(),
      completed: true,
      createdAt: serverTimestamp(),
    });
  }
  return ref.id;
}

// 取得某日的 progress docId（若存在）
async function getProgressDocId(uid, habitId, date) {
  const q1 = query(
    collection(db, "progress"),
    where("userID", "==", uid),
    where("habitId", "==", habitId),
    where("date", "==", date),
    limit(1)
  );
  const s = await getDocs(q1);
  return s.empty ? null : s.docs[0].id;
}

// 將某日設為 完成(true) / 未完成(false)（upsert）
export async function upsertProgress(uid, habitId, date, completed) {
  const existingId = await getProgressDocId(uid, habitId, date);
  if (completed) {
    if (!existingId) {
      await addDoc(collection(db, "progress"), {
        userID: uid, habitId, date, completed: true, createdAt: serverTimestamp(),
      });
    }
  } else {
    if (existingId) {
      await deleteDoc(doc(db, "progress", existingId));
    }
  }
}

// 批次設定多天（datesToState : { 'YYYY-MM-DD': true/false })
export async function setProgressForDays(uid, habitId, datesToState) {
  // 逐日 upsert（避免索引與過度依賴批次 API）
  const entries = Object.entries(datesToState);
  for (const [date, completed] of entries) {
    // 忽略未來日子（只允許今天與過去 6 天）
    const last7 = new Set(lastNDates(7));
    if (!last7.has(date)) continue;
    await upsertProgress(uid, habitId, date, !!completed);
  }
}

// Today 快捷
export async function setHabitDoneToday(uid, habitId, next) {
  await upsertProgress(uid, habitId, dayKey(), next);
}
