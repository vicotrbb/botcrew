import Avatar from 'boring-avatars';

const AVATAR_COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe'];

interface AgentAvatarProps {
  name: string;
  size?: number;
}

export function AgentAvatar({ name, size = 40 }: AgentAvatarProps) {
  return (
    <div className="rounded-full overflow-hidden flex-shrink-0" style={{ width: size, height: size }}>
      <Avatar size={size} name={name} variant="beam" colors={AVATAR_COLORS} />
    </div>
  );
}
