export function rollingMonths(now = new Date()) {
  return [0, 1, 2].map(offset => new Date(now.getFullYear(), now.getMonth() + offset, 1));
}

export function monthKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

export function isInRollingWindow(isoDate, now = new Date()) {
  if (!isoDate) return false;
  const key = isoDate.slice(0, 7);
  return rollingMonths(now).some(month => monthKey(month) === key);
}
