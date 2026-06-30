import React, { useState } from "react";
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
} from "react-native";

import ProfileHeader from "../../components/profile/ProfileHeader";

import TicketHeaderCard from "../../components/tickets/TicketHeaderCard";
import SectionTitle from "../../components/tickets/SectionTitle";
import TicketCategoryPicker from "../../components/tickets/TicketCategoryPicker";
import PrioritySelector from "../../components/tickets/PrioritySelector";
import SubjectInput from "../../components/tickets/SubjectInput";
import DescriptionInput from "../../components/tickets/DescriptionInput";
import AttachmentCard from "../../components/tickets/AttachmentCard";
import RaiseTicketButton from "../../components/tickets/RaiseTicketButton";
import TicketStatsCard from "../../components/tickets/TicketStatsCard";
import TicketCard from "../../components/tickets/TicketCard";
import EmptyTickets from "../../components/tickets/EmptyTickets";

export default function TicketsScreen() {
  const [category, setCategory] = useState("hr");
  const [priority, setPriority] = useState("Medium");
  const [subject, setSubject] = useState("");
  const [description, setDescription] =
    useState("");
  const [attachment, setAttachment] =
    useState("");
  const [loading, setLoading] =
    useState(false);

  const tickets = [
    {
      id: "TK-1001",
      category: "HR",
      subject: "Leave balance mismatch",
      priority: "Medium",
      status: "Open",
      createdAt: "18 Jul 2026",
    },
    {
      id: "TK-1002",
      category: "IT",
      subject: "Laptop VPN not working",
      priority: "High",
      status: "In Progress",
      createdAt: "15 Jul 2026",
    },
    {
      id: "TK-1003",
      category: "Payroll",
      subject: "Salary slip missing",
      priority: "Low",
      status: "Resolved",
      createdAt: "08 Jul 2026",
    },
  ];

  const handleRaiseTicket = () => {
    setLoading(true);

    setTimeout(() => {
      setLoading(false);

      console.log({
        category,
        priority,
        subject,
        description,
        attachment,
      });
    }, 1500);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ProfileHeader
        title="Support Tickets"
        showBack={false}
      />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.content}
      >
        <TicketHeaderCard
          totalTickets={12}
          openTickets={3}
          resolvedTickets={9}
        />

        <SectionTitle
          icon="create-outline"
          title="Raise New Ticket"
          subtitle="Submit your issue to the support team."
        />

        <TicketCategoryPicker
          selectedCategory={category}
          onSelectCategory={setCategory}
        />

        <PrioritySelector
          selectedPriority={priority}
          onSelectPriority={setPriority}
        />

        <SubjectInput
          value={subject}
          onChangeText={setSubject}
        />

        <DescriptionInput
          value={description}
          onChangeText={setDescription}
        />

        <AttachmentCard
          fileName={attachment}
          onUpload={() =>
            setAttachment("Screenshot.png")
          }
        />

        <RaiseTicketButton
          loading={loading}
          onPress={handleRaiseTicket}
        />

        <SectionTitle
          icon="stats-chart-outline"
          title="Ticket Overview"
          subtitle="Current support request statistics"
        />

        <TicketStatsCard
          open={3}
          inProgress={2}
          resolved={6}
          closed={9}
        />

        <SectionTitle
          icon="time-outline"
          title="Recent Tickets"
          subtitle="Track the status of your support requests"
        />

        {tickets.length === 0 ? (
          <EmptyTickets
            onCreateTicket={() => {}}
          />
        ) : (
          tickets.map((ticket) => (
            <TicketCard
              key={ticket.id}
              ticketId={ticket.id}
              category={ticket.category}
              subject={ticket.subject}
              priority={ticket.priority}
              status={ticket.status}
              createdAt={ticket.createdAt}
              onPress={() =>
                console.log(ticket.id)
              }
            />
          ))
        )}

        <SafeAreaView
          style={{ height: 110 }}
        />
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F8FAFC",
  },

  content: {
    paddingHorizontal: 18,
    paddingTop: 4,
    paddingBottom: 120,
  },

  card: {
    backgroundColor: "#FFFFFF",

    borderRadius: 22,

    padding: 20,

    marginBottom: 22,

    borderWidth: 1,
    borderColor: "#E8EDF3",

    shadowColor: "#0F172A",
    shadowOpacity: 0.04,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },

    elevation: 2,
  },

  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  section: {
    marginBottom: 22,
  },

  sectionSpacing: {
    marginTop: 8,
    marginBottom: 22,
  },

  divider: {
    height: 1,
    backgroundColor: "#EEF2F7",
    marginVertical: 18,
  },

  emptySpace: {
    height: 24,
  },

  footerSpace: {
    height: 110,
  },

  shadow: {
    shadowColor: "#0F172A",
    shadowOpacity: 0.05,
    shadowRadius: 10,
    shadowOffset: {
      width: 0,
      height: 5,
    },
    elevation: 3,
  },

  centered: {
    justifyContent: "center",
    alignItems: "center",
  },

  title: {
    fontSize: 20,
    fontWeight: "800",
    color: "#0F172A",
  },

  subtitle: {
    marginTop: 6,
    fontSize: 14,
    lineHeight: 22,
    color: "#64748B",
  },
});