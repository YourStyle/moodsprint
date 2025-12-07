'use client';

import { useState, useRef, useEffect } from 'react';
import { ArrowLeft, Send, Mic, ThumbsUp, ThumbsDown, Loader2, RefreshCw, Edit2 } from 'lucide-react';
import { Button, Card } from '@/components/ui';
import clsx from 'clsx';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
}

interface AIChatProps {
  onClose: () => void;
  onSendMessage?: (message: string) => Promise<string>;
}

export function AIChat({ onClose, onSendMessage }: AIChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Add loading message
    const loadingId = (Date.now() + 1).toString();
    setMessages((prev) => [
      ...prev,
      {
        id: loadingId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isLoading: true,
      },
    ]);

    try {
      // Call API or use default response
      const response = onSendMessage
        ? await onSendMessage(input.trim())
        : await mockAIResponse(input.trim());

      // Replace loading message with actual response
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingId
            ? { ...msg, content: response, isLoading: false }
            : msg
        )
      );
    } catch (error) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingId
            ? {
                ...msg,
                content: 'Sorry, I encountered an error. Please try again.',
                isLoading: false,
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full min-h-screen bg-gradient-to-b from-dark-900 to-dark-700">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-purple-500/10">
        <button
          onClick={onClose}
          className="p-2 text-gray-400 hover:text-white rounded-full hover:bg-purple-500/20 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-lg font-semibold text-white">New Chat</h1>
        <div className="w-9" /> {/* Spacer for centering */}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center mb-4">
              <span className="text-2xl">✨</span>
            </div>
            <h2 className="text-xl font-semibold text-white mb-2">
              How can I help you today?
            </h2>
            <p className="text-gray-400 max-w-xs">
              Ask me anything about productivity, task planning, or how to manage your energy better.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-purple-500/10">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Send a message..."
              className="w-full px-4 py-3 pr-12 glass-input rounded-2xl text-white placeholder-gray-500"
              disabled={isLoading}
            />
            <button
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-purple-400 hover:text-purple-300 transition-colors"
              aria-label="Voice input"
            >
              <Mic className="w-5 h-5" />
            </button>
          </div>
          <Button
            variant="gradient"
            size="md"
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="!rounded-full !p-3"
          >
            <Send className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={clsx('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={clsx(
          'max-w-[85%] rounded-2xl p-4',
          isUser
            ? 'bg-purple-600 text-white rounded-br-sm'
            : 'glass-card rounded-bl-sm'
        )}
      >
        {/* Header for assistant */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <span className="text-xs">✨</span>
            </div>
            <span className="text-sm font-medium text-purple-400">Neura AI</span>
            {message.isLoading && (
              <RefreshCw className="w-4 h-4 text-purple-400 animate-spin" />
            )}
          </div>
        )}

        {/* User header with edit button */}
        {isUser && (
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-purple-200">You</span>
            <button className="p-1 text-purple-200 hover:text-white transition-colors">
              <Edit2 className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* Content */}
        {message.isLoading ? (
          <div className="flex items-center gap-2 text-gray-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Thinking...</span>
          </div>
        ) : (
          <p className={clsx('text-sm whitespace-pre-wrap', isUser ? 'text-white' : 'text-gray-200')}>
            {message.content}
          </p>
        )}

        {/* Feedback buttons for assistant */}
        {!isUser && !message.isLoading && (
          <div className="flex items-center gap-2 mt-3 pt-2 border-t border-purple-500/10">
            <button className="p-1.5 text-gray-500 hover:text-green-400 transition-colors rounded-lg hover:bg-green-500/10">
              <ThumbsUp className="w-4 h-4" />
            </button>
            <button className="p-1.5 text-gray-500 hover:text-red-400 transition-colors rounded-lg hover:bg-red-500/10">
              <ThumbsDown className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// Mock AI response for demo
async function mockAIResponse(input: string): Promise<string> {
  await new Promise((resolve) => setTimeout(resolve, 1500));

  const responses = [
    `Great question! To create an impressive design case study presentation, think of it like telling a clear, engaging story.\n\nStart with a short, friendly introduction — explain what the project is, who it was for, and why it matters.\n\nAnd if you'd like to dig deeper, you could check out a few great resources:\n\n1. **Coursera Design Course**: https://coursera.org/specializations/interaction-design\n\n2. **LinkedIn Case Study Crash Course**: https://linkedin.com/learning/building-your-ux-portfolio`,
    `I'd be happy to help you with that! Based on your current energy level, here are some suggestions:\n\n1. Start with smaller, manageable tasks\n2. Take regular breaks (every 25 minutes)\n3. Focus on one task at a time\n\nWould you like me to create a task breakdown for you?`,
    `That's a thoughtful question! Here's what I recommend:\n\n**For low energy days:**\n- Administrative tasks\n- Reading and research\n- Planning sessions\n\n**For high energy:**\n- Creative work\n- Complex problem-solving\n- Important meetings`,
  ];

  return responses[Math.floor(Math.random() * responses.length)];
}
