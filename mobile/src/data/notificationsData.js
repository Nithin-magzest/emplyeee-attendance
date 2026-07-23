export const notificationFilters = [
  "All",
  "Unread",
  "HR",
  "Attendance",
  "Leave",
];

export const notifications = [
  {
    id: "1",
    type: "HR",
    title: "Welcome to the Company",
    message:
      "We are excited to have you on board. Please complete your onboarding tasks before Friday.",
    time: "Just now",
    unread: true,
    icon: "people",
    color: "#2563EB",
  },

  {
    id: "2",
    type: "Attendance",
    title: "Attendance Reminder",
    message:
      "You have not checked in today. Please mark your attendance before 10:00 AM.",
    time: "15 min ago",
    unread: true,
    icon: "calendar",
    color: "#16A34A",
  },

  {
    id: "3",
    type: "Leave",
    title: "Leave Approved",
    message:
      "Your leave request for 14 July has been approved by your reporting manager.",
    time: "1 hour ago",
    unread: false,
    icon: "checkmark-circle",
    color: "#22C55E",
  },

  {
    id: "4",
    type: "HR",
    title: "Salary Credited",
    message:
      "Your salary for this month has been successfully credited to your bank account.",
    time: "Today",
    unread: false,
    icon: "wallet",
    color: "#F59E0B",
  },

  {
    id: "5",
    type: "Attendance",
    title: "Regularization Request",
    message:
      "Your attendance regularization request has been approved successfully.",
    time: "Yesterday",
    unread: false,
    icon: "time",
    color: "#8B5CF6",
  },

  {
    id: "6",
    type: "Leave",
    title: "Leave Balance Updated",
    message:
      "Your annual leave balance has been updated after your recent approval.",
    time: "Yesterday",
    unread: false,
    icon: "document-text",
    color: "#0EA5E9",
  },

  {
    id: "7",
    type: "HR",
    title: "Company Holiday",
    message:
      "Monday has been declared an optional holiday due to the upcoming festival.",
    time: "2 days ago",
    unread: true,
    icon: "gift",
    color: "#EF4444",
  },

  {
    id: "8",
    type: "Attendance",
    title: "Late Check-in",
    message:
      "Your attendance has been marked as late today. Please ensure timely check-in.",
    time: "3 days ago",
    unread: false,
    icon: "alarm",
    color: "#F97316",
  },
];