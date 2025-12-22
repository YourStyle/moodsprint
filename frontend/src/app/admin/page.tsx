'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Shield, Users, Calendar, UserMinus, ChevronRight } from 'lucide-react';
import { Card, Button, Input, Modal } from '@/components/ui';
import { gamificationService } from '@/services';
import { useAppStore } from '@/lib/store';

// Activity heatmap component
function ActivityHeatmap({ activity }: { activity: Record<string, number> }) {
  const today = new Date();
  const startDate = new Date(today);
  startDate.setDate(startDate.getDate() - 365);

  // Generate all days for the last year
  const days: { date: string; count: number; dayOfWeek: number }[] = [];
  const current = new Date(startDate);

  while (current <= today) {
    const dateStr = current.toISOString().split('T')[0];
    days.push({
      date: dateStr,
      count: activity[dateStr] || 0,
      dayOfWeek: current.getDay(),
    });
    current.setDate(current.getDate() + 1);
  }

  // Group by weeks
  const weeks: typeof days[] = [];
  let currentWeek: typeof days = [];

  // Pad first week with empty days if needed
  const firstDayOfWeek = days[0]?.dayOfWeek || 0;
  for (let i = 0; i < firstDayOfWeek; i++) {
    currentWeek.push({ date: '', count: -1, dayOfWeek: i });
  }

  for (const day of days) {
    currentWeek.push(day);
    if (day.dayOfWeek === 6) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  }
  if (currentWeek.length > 0) {
    weeks.push(currentWeek);
  }

  const getColor = (count: number) => {
    if (count < 0) return 'bg-transparent';
    if (count === 0) return 'bg-gray-800';
    if (count <= 2) return 'bg-green-900';
    if (count <= 4) return 'bg-green-700';
    if (count <= 6) return 'bg-green-500';
    return 'bg-green-400';
  };

  const months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'];

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-0.5 min-w-[700px]">
        {weeks.map((week, weekIndex) => (
          <div key={weekIndex} className="flex flex-col gap-0.5">
            {week.map((day, dayIndex) => (
              <div
                key={dayIndex}
                className={`w-3 h-3 rounded-sm ${getColor(day.count)}`}
                title={day.date ? `${day.date}: ${day.count} завершено` : ''}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="flex justify-between mt-2 text-xs text-gray-500">
        {months.map((month) => (
          <span key={month}>{month}</span>
        ))}
      </div>
      <div className="flex items-center gap-2 mt-3 text-xs text-gray-400">
        <span>Меньше</span>
        <div className="flex gap-0.5">
          <div className="w-3 h-3 rounded-sm bg-gray-800" />
          <div className="w-3 h-3 rounded-sm bg-green-900" />
          <div className="w-3 h-3 rounded-sm bg-green-700" />
          <div className="w-3 h-3 rounded-sm bg-green-500" />
          <div className="w-3 h-3 rounded-sm bg-green-400" />
        </div>
        <span>Больше</span>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const queryClient = useQueryClient();
  const { user } = useAppStore();
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [showRemoveFriend, setShowRemoveFriend] = useState(false);
  const [removeFriendUserId, setRemoveFriendUserId] = useState('');
  const [removeFriendFriendId, setRemoveFriendFriendId] = useState('');

  // Fetch all users
  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => gamificationService.getAdminUsers(),
    enabled: !!user,
  });

  // Fetch selected user's activity
  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ['admin', 'activity', selectedUserId],
    queryFn: () => gamificationService.getUserActivity(selectedUserId!),
    enabled: !!selectedUserId,
  });

  // Remove friend mutation
  const removeFriendMutation = useMutation({
    mutationFn: ({ userId, friendId }: { userId: number; friendId: number }) =>
      gamificationService.removeFriend(userId, friendId),
    onSuccess: () => {
      setShowRemoveFriend(false);
      setRemoveFriendUserId('');
      setRemoveFriendFriendId('');
      queryClient.invalidateQueries({ queryKey: ['friends'] });
    },
  });

  const users = usersData?.data?.users || [];
  const activity = activityData?.data?.activity || {};
  const selectedUser = activityData?.data;

  if (!user) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">Войдите для доступа к админке</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="text-center mb-4">
        <Shield className="w-10 h-10 text-purple-500 mx-auto mb-2" />
        <h1 className="text-2xl font-bold text-white">Админ панель</h1>
      </div>

      {/* Quick Actions */}
      <Card>
        <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <UserMinus className="w-4 h-4" />
          Удаление друзей
        </h3>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowRemoveFriend(true)}
        >
          Удалить дружбу
        </Button>
      </Card>

      {/* Users List */}
      <Card>
        <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
          <Users className="w-4 h-4" />
          Пользователи ({users.length})
        </h3>
        {usersLoading ? (
          <div className="text-gray-400 text-sm">Загрузка...</div>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {users.map((u) => (
              <button
                key={u.id}
                onClick={() => setSelectedUserId(u.id)}
                className={`w-full flex items-center justify-between p-2 rounded-lg transition-colors ${
                  selectedUserId === u.id
                    ? 'bg-purple-500/20 border border-purple-500/50'
                    : 'bg-gray-800 hover:bg-gray-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-white text-xs font-bold">
                    {u.first_name?.[0] || u.username?.[0] || '?'}
                  </div>
                  <div className="text-left">
                    <p className="text-sm text-white">{u.first_name || u.username || `ID: ${u.id}`}</p>
                    <p className="text-xs text-gray-400">Уровень {u.level} | {u.xp} XP</p>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </button>
            ))}
          </div>
        )}
      </Card>

      {/* Activity Heatmap */}
      {selectedUserId && (
        <Card>
          <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            Активность: {selectedUser?.first_name || selectedUser?.username || `ID: ${selectedUserId}`}
          </h3>
          {activityLoading ? (
            <div className="text-gray-400 text-sm">Загрузка...</div>
          ) : (
            <ActivityHeatmap activity={activity} />
          )}
        </Card>
      )}

      {/* Remove Friend Modal */}
      <Modal
        isOpen={showRemoveFriend}
        onClose={() => setShowRemoveFriend(false)}
        title="Удалить дружбу"
      >
        <div className="space-y-4">
          <Input
            label="User ID"
            type="number"
            value={removeFriendUserId}
            onChange={(e) => setRemoveFriendUserId(e.target.value)}
            placeholder="ID первого пользователя"
          />
          <Input
            label="Friend ID"
            type="number"
            value={removeFriendFriendId}
            onChange={(e) => setRemoveFriendFriendId(e.target.value)}
            placeholder="ID второго пользователя"
          />
          <Button
            className="w-full"
            variant="danger"
            onClick={() => {
              const userId = parseInt(removeFriendUserId);
              const friendId = parseInt(removeFriendFriendId);
              if (userId && friendId) {
                removeFriendMutation.mutate({ userId, friendId });
              }
            }}
            isLoading={removeFriendMutation.isPending}
            disabled={!removeFriendUserId || !removeFriendFriendId}
          >
            Удалить дружбу
          </Button>
        </div>
      </Modal>
    </div>
  );
}
