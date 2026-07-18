'use client';

import { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Bot, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import styles from './AICopilot.module.css';

export default function AICopilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I am VoltEdge AI Copilot. Ask me anything about your fleet, battery health, supply chain, or carbon emissions.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      let moduleContext = null;
      if (typeof window !== 'undefined') {
        const path = window.location.pathname;
        if (path.includes('battery')) moduleContext = 'battery';
        else if (path.includes('fleet')) moduleContext = 'fleet';
        else if (path.includes('supply-chain')) moduleContext = 'supply-chain';
        else if (path.includes('carbon') || path.includes('net-zero')) moduleContext = 'carbon';
      }

      const response = await api.chat(userMessage, moduleContext);
      setMessages(prev => [...prev, { role: 'assistant', content: response.response }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error connecting to the AI service.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button 
        className={`${styles.fab} ${isOpen ? styles.hidden : ''}`}
        onClick={() => setIsOpen(true)}
      >
        <MessageSquare size={24} />
      </button>

      <div className={`${styles.chatContainer} ${isOpen ? styles.open : ''}`}>
        <div className={styles.header}>
          <div className={styles.headerTitle}>
            <Bot size={20} style={{ color: 'var(--primary)' }} />
            <span>VoltEdge Copilot</span>
          </div>
          <button onClick={() => setIsOpen(false)} className={styles.closeButton}>
            <X size={20} />
          </button>
        </div>

        <div className={styles.messageList}>
          {messages.map((msg, idx) => (
            <div key={idx} className={`${styles.messageWrapper} ${msg.role === 'user' ? styles.userWrapper : styles.assistantWrapper}`}>
              {msg.role === 'assistant' && (
                <div className={styles.avatar}>
                  <Bot size={16} />
                </div>
              )}
              <div className={`${styles.message} ${msg.role === 'user' ? styles.userMessage : styles.assistantMessage}`}>
                <div dangerouslySetInnerHTML={{ __html: msg.content.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
              </div>
            </div>
          ))}
          {loading && (
            <div className={`${styles.messageWrapper} ${styles.assistantWrapper}`}>
              <div className={styles.avatar}>
                <Loader2 size={16} className="animate-pulse" />
              </div>
              <div className={`${styles.message} ${styles.assistantMessage}`}>
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className={styles.inputArea}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask AI Copilot..."
            className={styles.input}
            disabled={loading}
          />
          <button type="submit" disabled={!input.trim() || loading} className={styles.sendButton}>
            <Send size={18} />
          </button>
        </form>
      </div>
    </>
  );
}
