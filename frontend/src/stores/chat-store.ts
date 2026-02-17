import { create } from 'zustand';

interface ChatState {
  isOpen: boolean;
  activeChannelId: string | null;
  unreadCounts: Record<string, number>;
}

interface ChatActions {
  toggle: () => void;
  open: () => void;
  close: () => void;
  setActiveChannel: (id: string | null) => void;
  incrementUnread: (channelId: string) => void;
  clearUnread: (channelId: string) => void;
  setUnreadCount: (channelId: string, count: number) => void;
}

export const useChatStore = create<ChatState & ChatActions>((set) => ({
  isOpen: true,
  activeChannelId: null,
  unreadCounts: {},

  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),

  setActiveChannel: (id) => set({ activeChannelId: id }),

  incrementUnread: (channelId) =>
    set((state) => ({
      unreadCounts: {
        ...state.unreadCounts,
        [channelId]: (state.unreadCounts[channelId] ?? 0) + 1,
      },
    })),

  clearUnread: (channelId) =>
    set((state) => ({
      unreadCounts: {
        ...state.unreadCounts,
        [channelId]: 0,
      },
    })),

  setUnreadCount: (channelId, count) =>
    set((state) => ({
      unreadCounts: {
        ...state.unreadCounts,
        [channelId]: count,
      },
    })),
}));
