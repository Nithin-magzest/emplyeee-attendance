export const policyTabs = [
  {
    id: "terms",
    title: "Terms",
    icon: "document-text-outline",
  },
  {
    id: "rules",
    title: "Rules",
    icon: "clipboard-outline",
  },
  {
    id: "limitations",
    title: "Limitations",
    icon: "warning-outline",
  },
  {
    id: "instructions",
    title: "Instructions",
    icon: "hammer-outline",
  },
  {
    id: "posh",
    title: "POSH",
    icon: "shield-checkmark-outline",
  },
  {
    id: "resignation",
    title: "Resignation",
    icon: "log-out-outline",
  },
];

export const policies = {
  terms: {
    banner: {
      type: "info",
      title: "Effective Date",
      message:
        "These terms are effective from your date of joining and govern your use of the employee portal.",
    },

    sections: [
      {
        title: "1. Acceptance of Terms",
        bullets: [
          "By using this portal you agree to comply with all company policies.",
          "Portal access is restricted to authorized employees only.",
          "Misuse of company systems may result in disciplinary action.",
        ],
      },
      {
        title: "2. Employee Credentials & Account Security",
        bullets: [
          "Keep your login credentials confidential.",
          "Do not share passwords with anyone.",
          "Report suspicious login activity immediately.",
          "Enable password updates every 90 days.",
        ],
      },
      {
        title: "3. Accuracy of Information",
        bullets: [
          "Employee information must always be accurate.",
          "Attendance records are official company records.",
          "False information may lead to disciplinary action.",
        ],
      },
      {
        title: "4. Attendance & Leave",
        bullets: [
          "Attendance should be marked honestly.",
          "Leave requests require manager approval.",
          "Leave misuse will be investigated.",
        ],
      },
      {
        title: "5. Data Privacy",
        bullets: [
          "Employee information is confidential.",
          "Data is processed according to company privacy standards.",
          "Personal data cannot be shared without authorization.",
        ],
      },
    ],
  },

  rules: {
    banner: {
      type: "success",
      title: "Company Rules",
      message:
        "These rules apply equally to all employees regardless of department or designation.",
    },

    sections: [
      {
        title: "1. Punctuality",
        bullets: [
          "Report to work on time.",
          "Repeated late arrivals may attract warnings.",
          "Unauthorized absence affects payroll.",
        ],
      },
      {
        title: "2. Dress Code",
        bullets: [
          "Maintain professional appearance.",
          "Wear company ID while inside office.",
          "Follow department-specific dress policies.",
        ],
      },
      {
        title: "3. Workplace Conduct",
        bullets: [
          "Treat everyone respectfully.",
          "Avoid abusive language.",
          "Violence or harassment is prohibited.",
        ],
      },
      {
        title: "4. Office Resources",
        bullets: [
          "Use company resources responsibly.",
          "Personal usage should remain minimal.",
          "Unauthorized software installation is prohibited.",
        ],
      },
    ],
  },

  limitations: {
    banner: {
      type: "warning",
      title: "Important",
      message:
        "These limitations exist to maintain a secure, compliant and productive workplace.",
    },

    sections: [
      {
        title: "1. Working Hours",
        bullets: [
          "Overtime requires prior approval.",
          "Working beyond company limits requires HR permission.",
        ],
      },
      {
        title: "2. Leave Restrictions",
        bullets: [
          "Back-to-back leave requires approval.",
          "Medical certificate may be required.",
        ],
      },
      {
        title: "3. Internet Usage",
        bullets: [
          "Illegal websites are prohibited.",
          "Heavy personal internet usage is not allowed.",
        ],
      },
      {
        title: "4. Client Interaction",
        bullets: [
          "Do not negotiate contracts without approval.",
          "All commitments require management authorization.",
        ],
      },
    ],
  },

  instructions: {
    banner: {
      type: "primary",
      title: "Portal Instructions",
      message:
        "Follow these instructions to use the employee portal effectively.",
    },

    sections: [
      {
        title: "Attendance",
        bullets: [
          "Mark attendance using QR or Face Scan.",
          "Report attendance issues through Support Tickets.",
        ],
      },
      {
        title: "Leave",
        bullets: [
          "Apply leave before the required date.",
          "Track leave status from Leave History.",
        ],
      },
      {
        title: "Support Tickets",
        bullets: [
          "Raise tickets with clear descriptions.",
          "Avoid duplicate tickets.",
        ],
      },
      {
        title: "Profile",
        bullets: [
          "Keep your personal information updated.",
          "Critical information requires HR verification.",
        ],
      },
    ],
  },

  posh: {
    banner: {
      type: "danger",
      title: "Legal Mandate",
      message:
        "The POSH policy ensures a safe, respectful and harassment-free workplace.",
    },

    sections: [
      {
        title: "Purpose",
        bullets: [
          "Provide a safe workplace.",
          "Prevent sexual harassment.",
          "Protect employee dignity.",
        ],
      },
      {
        title: "Complaint Process",
        bullets: [
          "Complaints should be submitted confidentially.",
          "ICC investigates complaints.",
          "All proceedings remain confidential.",
        ],
      },
      {
        title: "Zero Tolerance",
        bullets: [
          "Retaliation is prohibited.",
          "False complaints may attract action.",
          "Annual POSH training is mandatory.",
        ],
      },
    ],
  },

  resignation: {
    banner: {
      type: "warning",
      title: "Important",
      message:
        "Read the resignation policy carefully before submitting your resignation.",
    },

    sections: [
      {
        title: "Notice Period",
        bullets: [
          "Serve the required notice period.",
          "Notice depends on employment contract.",
        ],
      },
      {
        title: "Exit Process",
        bullets: [
          "Complete knowledge transfer.",
          "Return company assets.",
          "Clear pending responsibilities.",
        ],
      },
      {
        title: "Final Settlement",
        bullets: [
          "Settlement is processed after clearance.",
          "Salary, leave encashment and reimbursements are included.",
        ],
      },
      {
        title: "Relieving Letter",
        bullets: [
          "Issued after successful completion of exit formalities.",
        ],
      },
    ],
  },
};