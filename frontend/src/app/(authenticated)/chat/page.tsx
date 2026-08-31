"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "../../../context/AuthContext";
import { apiClient, ApiClientError } from "../../../lib/api-client";
import { ChatMessage, ChatMessageProps } from "../../../components/chat/ChatMessage";

function generateSessionId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return `sess_${crypto.randomUUID().slice(0, 8)}`;
  }
  return `sess_${Math.random().toString(36).slice(2, 10)}`;
}

export default function ChatPage() {
  const { user } = useAuth();
  const [sessionId, setSessionId] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessageProps[]>([]);
  const [inputText, setInputText] = useState<string>("");
  const [isSending, setIsSending] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Initialize or restore conversation session
  useEffect(() => {
    let activeSession = "";
    if (typeof window !== "undefined") {
      activeSession = sessionStorage.getItem("caregraph_chat_session") || "";
      if (!activeSession) {
        activeSession = generateSessionId();
        sessionStorage.setItem("caregraph_chat_session", activeSession);
      }
    } else {
      activeSession = generateSessionId();
    }
    setSessionId(activeSession);

    // Initial greeting
    setMessages([
      {
        id: "msg_init",
        role: "assistant",
        content: `Hello ${user?.username || "there"}! I am your CareGraph Care Coordinator. How can I help you today? You can describe symptoms, ask for appointment scheduling, or manage your health records.`,
        intent: "general",
        sources: [],
        followUpQuestions: [
          "I have had fever and cough for three days",
          "I need an appointment with a cardiologist tomorrow",
          "Check my active prescribed medications",
        ],
      },
    ]);
  }, [user?.username]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending, isApproving]);

  const handleResetSession = () => {
    const newSession = generateSessionId();
    if (typeof window !== "undefined") {
      sessionStorage.setItem("caregraph_chat_session", newSession);
    }
    setSessionId(newSession);
    setErrorMessage(null);
    setMessages([
      {
        id: `msg_reset_${Date.now()}`,
        role: "assistant",
        content: `New coordination session started. How can I help you today?`,
        intent: "general",
        sources: [],
        followUpQuestions: [
          "I have had a mild headache since yesterday",
          "Find available dermatologist slots",
          "What are my logged vitals?",
        ],
      },
    ]);
  };

  const handleSendMessage = async (textToSend?: string) => {
    const message = (textToSend !== undefined ? textToSend : inputText).trim();
    if (!message || isSending) return;

    setInputText("");
    setErrorMessage(null);

    const userMessageId = `msg_user_${Date.now()}`;
    const newMessages: ChatMessageProps[] = [
      ...messages,
      {
        id: userMessageId,
        role: "user",
        content: message,
      },
    ];
    setMessages(newMessages);
    setIsSending(true);

    try {
      const response = await apiClient.sendChatMessage({
        message,
        session_id: sessionId,
      });

      const assistantMsgId = `msg_assistant_${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMsgId,
          role: "assistant",
          content: response.message,
          intent: response.intent,
          riskLevel: response.risk_level,
          safetyEscalated: response.safety_escalated,
          sources: response.sources || [],
          followUpQuestions: response.follow_up_questions || [],
          approvalRequired: response.approval_required,
          approvalStatus: response.approval_status || (response.approval_required ? "pending" : null),
          selectedSlot: response.selected_slot,
        },
      ]);
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        if (err.status === 401) {
          setErrorMessage("Your session has expired. Please sign in again.");
        } else if (err.status === 429) {
          setErrorMessage("The AI coordinator is temporarily busy. Please wait a moment and retry.");
        } else if (err.status === 504) {
          setErrorMessage("Request timed out. Please try again.");
        } else {
          setErrorMessage(err.detail || "Error communicating with coordination service.");
        }
      } else {
        setErrorMessage("Network error: Could not reach the CareGraph API.");
      }
    } finally {
      setIsSending(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleHitlDecision = useCallback(
    async (decision: "approved" | "rejected", targetMessageId: string) => {
      setIsApproving(true);
      setErrorMessage(null);
      try {
        const response = await apiClient.approveCoordination({
          session_id: sessionId,
          decision,
        });

        // Update the approval status on the original message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === targetMessageId
              ? {
                  ...msg,
                  approvalRequired: false,
                  approvalStatus: decision,
                }
              : msg
          )
        );

        // Append the resumed LangGraph response
        const confirmMsgId = `msg_resume_${Date.now()}`;
        setMessages((prev) => [
          ...prev,
          {
            id: confirmMsgId,
            role: "assistant",
            content: response.message,
            intent: response.intent,
            riskLevel: response.risk_level,
            safetyEscalated: response.safety_escalated,
            sources: response.sources || [],
            followUpQuestions: response.follow_up_questions || [],
            approvalRequired: false,
            approvalStatus: decision,
          },
        ]);
      } catch (err: unknown) {
        if (err instanceof ApiClientError) {
          setErrorMessage(err.detail || `Failed to record approval decision (${err.status}).`);
        } else {
          setErrorMessage("Failed to send approval decision to the server.");
        }
      } finally {
        setIsApproving(false);
      }
    },
    [sessionId]
  );

  return (
    <div className="chat-container">
      {/* Header bar */}
      <div className="chat-header">
        <div className="flex items-center gap-3">
          <span style={{ fontSize: "1.3rem" }}>💬</span>
          <div>
            <h3 style={{ fontSize: "var(--font-size-base)", color: "var(--text-primary)", margin: 0 }}>
              AI Care Coordinator
            </h3>
            <span style={{ fontSize: "0.7rem", color: "var(--text-dim)" }}>
              Thread: <code style={{ color: "var(--text-muted)" }}>{sessionId || "loading..."}</code>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleResetSession}
            style={{ fontSize: "var(--font-size-xs)", padding: "0.35rem 0.75rem" }}
            title="Start a fresh conversation thread"
          >
            🔄 New Session
          </button>
        </div>
      </div>

      {/* Message List */}
      <div className="chat-messages" role="log" aria-live="polite">
        {messages.map((msg) => (
          <ChatMessage
            key={msg.id}
            {...msg}
            onApprove={() => handleHitlDecision("approved", msg.id)}
            onReject={() => handleHitlDecision("rejected", msg.id)}
            onSelectFollowUp={(q) => handleSendMessage(q)}
            isApproving={isApproving}
          />
        ))}

        {/* Loading Bubble */}
        {isSending && (
          <div className="message-row assistant">
            <div className="message-avatar assistant">🧬</div>
            <div className="message-bubble assistant">
              <div className="flex items-center gap-2" style={{ color: "var(--text-muted)", fontSize: "var(--font-size-xs)" }}>
                <div className="spinner" style={{ width: "14px", height: "14px", borderWidth: "2px" }} />
                <span>Analyzing request & coordinating agents...</span>
              </div>
            </div>
          </div>
        )}

        {/* Error Alert */}
        {errorMessage && (
          <div
            className="card"
            style={{
              backgroundColor: "var(--status-emergency-bg)",
              borderColor: "var(--status-emergency-border)",
              padding: "var(--space-3)",
            }}
            role="alert"
          >
            <p style={{ color: "var(--status-emergency)", fontSize: "var(--font-size-xs)", fontWeight: 600, margin: 0 }}>
              ⚠️ {errorMessage}
            </p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <form
        className="chat-input-bar"
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }}
      >
        <input
          ref={inputRef}
          type="text"
          className="input"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Type your symptoms, doctor preferences, or questions..."
          disabled={isSending || isApproving}
          aria-label="Chat input query"
        />

        <button
          type="submit"
          className="btn btn-primary"
          disabled={!inputText.trim() || isSending || isApproving}
          aria-label="Send message"
        >
          {isSending ? (
            <div className="spinner" style={{ width: "16px", height: "16px" }} />
          ) : (
            "Send ✈️"
          )}
        </button>
      </form>
    </div>
  );
}
