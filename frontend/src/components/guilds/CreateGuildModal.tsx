'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, Loader2 } from 'lucide-react';
import { Modal, Button } from '@/components/ui';
import { guildsService } from '@/services';
import { hapticFeedback } from '@/lib/telegram';

interface CreateGuildModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const EMOJI_OPTIONS = ['🛡️', '⚔️', '🔥', '💎', '🌟', '🐉', '🦁', '🦅', '🐺', '🎯', '💀', '👑'];

export function CreateGuildModal({ isOpen, onClose, onSuccess }: CreateGuildModalProps) {
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [emoji, setEmoji] = useState('🛡️');
  const [isPublic, setIsPublic] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () => guildsService.createGuild({
      name,
      description: description || undefined,
      emoji,
      is_public: isPublic,
    }),
    onSuccess: (result) => {
      if (result.success) {
        hapticFeedback('success');
        queryClient.invalidateQueries({ queryKey: ['guilds'] });
        resetForm();
        onClose();
        onSuccess?.();
      } else {
        setError(result.error?.message || 'Ошибка создания гильдии');
        hapticFeedback('error');
      }
    },
    onError: () => {
      setError('Ошибка создания гильдии');
      hapticFeedback('error');
    },
  });

  const resetForm = () => {
    setName('');
    setDescription('');
    setEmoji('🛡️');
    setIsPublic(true);
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Введите название гильдии');
      return;
    }

    if (name.length < 3) {
      setError('Название должно быть минимум 3 символа');
      return;
    }

    if (name.length > 30) {
      setError('Название должно быть максимум 30 символов');
      return;
    }

    createMutation.mutate();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Создать гильдию">
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Emoji selector */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Эмблема гильдии
          </label>
          <div className="flex flex-wrap gap-2">
            {EMOJI_OPTIONS.map((e) => (
              <button
                key={e}
                type="button"
                onClick={() => setEmoji(e)}
                className={`w-10 h-10 rounded-lg text-xl flex items-center justify-center transition-all ${
                  emoji === e
                    ? 'bg-purple-600 ring-2 ring-purple-400 ring-offset-2 ring-offset-gray-900'
                    : 'bg-gray-700/50 hover:bg-gray-700'
                }`}
              >
                {e}
              </button>
            ))}
          </div>
        </div>

        {/* Name input */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Название *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Введите название гильдии"
            maxLength={30}
            className="w-full bg-gray-800/50 border border-gray-700/50 rounded-xl py-3 px-4 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
          />
          <div className="text-xs text-gray-500 mt-1 text-right">
            {name.length}/30
          </div>
        </div>

        {/* Description input */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Описание
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Расскажите о вашей гильдии..."
            maxLength={200}
            rows={3}
            className="w-full bg-gray-800/50 border border-gray-700/50 rounded-xl py-3 px-4 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors resize-none"
          />
          <div className="text-xs text-gray-500 mt-1 text-right">
            {description.length}/200
          </div>
        </div>

        {/* Public toggle */}
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-white">Публичная гильдия</div>
            <div className="text-xs text-gray-400">Любой сможет вступить</div>
          </div>
          <button
            type="button"
            onClick={() => setIsPublic(!isPublic)}
            className={`w-12 h-6 rounded-full transition-colors ${
              isPublic ? 'bg-purple-600' : 'bg-gray-600'
            }`}
          >
            <div className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform ${
              isPublic ? 'translate-x-6' : 'translate-x-0.5'
            }`} />
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="text-red-400 text-sm text-center bg-red-500/10 rounded-lg py-2 px-3">
            {error}
          </div>
        )}

        {/* Submit button */}
        <Button
          type="submit"
          disabled={createMutation.isPending || !name.trim()}
          className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
        >
          {createMutation.isPending ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Создание...
            </>
          ) : (
            <>
              <Shield className="w-4 h-4 mr-2" />
              Создать гильдию
            </>
          )}
        </Button>
      </form>
    </Modal>
  );
}
