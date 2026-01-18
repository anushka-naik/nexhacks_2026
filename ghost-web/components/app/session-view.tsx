'use client';

import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import { useRoomContext, useSessionContext, useSessionMessages } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { ChatTranscript } from '@/components/app/chat-transcript';
import { PreConnectMessage } from '@/components/app/preconnect-message';
import { TileLayout } from '@/components/app/tile-layout';
import {
  AgentControlBar,
  type ControlBarControls,
} from '@/components/livekit/agent-control-bar/agent-control-bar';
import { cn } from '@/lib/utils';
import { ScrollArea } from '../livekit/scroll-area/scroll-area';

const MotionBottom = motion.create('div');

const BOTTOM_VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.5,
    ease: 'easeOut',
  },
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({ top = false, bottom = false, className }: FadeProps) {
  return (
    <div
      className={cn(
        'from-background pointer-events-none h-4 bg-linear-to-b to-transparent',
        top && 'bg-linear-to-b',
        bottom && 'bg-linear-to-t',
        className
      )}
    />
  );
}

type TodoTask = {
  id: string;
  text: string;
};

type TodoCategory = {
  id: string;
  name: string;
  tasks: TodoTask[];
};

type TodoSnapshot = {
  type: 'TODO_SNAPSHOT';
  generated_at: string;
  categories: TodoCategory[];
};

interface SessionViewProps {
  appConfig: AppConfig;
}

export const SessionView = ({
  appConfig,
  ...props
}: React.ComponentProps<'section'> & SessionViewProps) => {
  const session = useSessionContext();
  const room = useRoomContext();
  const { messages } = useSessionMessages(session);
  const [chatOpen, setChatOpen] = useState(false);
  const [todoSnapshot, setTodoSnapshot] = useState<TodoSnapshot | null>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  const controls: ControlBarControls = {
    leave: true,
    microphone: true,
    chat: appConfig.supportsChatInput,
    camera: appConfig.supportsVideoInput,
    screenShare: appConfig.supportsScreenShare,
  };

  useEffect(() => {
    const lastMessage = messages.at(-1);
    const lastMessageIsLocal = lastMessage?.from?.isLocal === true;

    if (scrollAreaRef.current && lastMessageIsLocal) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (!room) {
      return;
    }

    const decoder = new TextDecoder();

    const handleDataReceived = (
      payload: Uint8Array,
      _participant: unknown,
      _kind: unknown,
      topic?: string
    ) => {
      if (topic !== 'todos') {
        return;
      }

      try {
        const text = decoder.decode(payload);
        const parsed = JSON.parse(text) as TodoSnapshot;
        if (parsed && parsed.type === 'TODO_SNAPSHOT') {
          setTodoSnapshot(parsed);
        }
      } catch (error) {
        console.error('Failed to parse todo snapshot', error);
      }
    };

    room.on('dataReceived', handleDataReceived);

    return () => {
      room.off('dataReceived', handleDataReceived);
    };
  }, [room]);

  return (
    <section className="bg-background relative z-10 h-full w-full overflow-hidden" {...props}>
      <div
        className={cn(
          'fixed inset-0 grid grid-cols-1 grid-rows-1',
          !chatOpen && 'pointer-events-none'
        )}
      >
        <Fade top className="absolute inset-x-4 top-0 h-40" />
        <ScrollArea ref={scrollAreaRef} className="px-4 pt-40 pb-[150px] md:px-6 md:pb-[200px]">
          <ChatTranscript
            hidden={!chatOpen}
            messages={messages}
            className="mx-auto max-w-2xl space-y-3 transition-opacity duration-300 ease-out"
          />
        </ScrollArea>
      </div>

      <TileLayout chatOpen={chatOpen} />

      <MotionBottom
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="fixed inset-x-3 bottom-0 z-50 md:inset-x-12"
      >
        {todoSnapshot && (
          <div className="bg-background/80 border-input/40 mb-3 max-h-60 overflow-hidden rounded-xl border px-3 py-2 text-xs shadow-sm backdrop-blur md:text-sm">
            <div className="flex items-center justify-between pb-1">
              <p className="font-medium">Live todos</p>
              <p className="text-muted-foreground text-[10px]">
                Updated {new Date(todoSnapshot.generated_at).toLocaleTimeString()}
              </p>
            </div>
            <div className="flex gap-4 overflow-x-auto">
              {todoSnapshot.categories.map((category) => (
                <div key={category.id} className="min-w-[120px]">
                  <p className="text-muted-foreground mb-1 text-[11px] font-semibold tracking-wide uppercase">
                    {category.name}
                  </p>
                  <ul className="space-y-1">
                    {category.tasks.map((task) => (
                      <li key={task.id} className="bg-muted/50 rounded px-2 py-1">
                        {task.text}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}
        {appConfig.isPreConnectBufferEnabled && (
          <PreConnectMessage messages={messages} className="pb-4" />
        )}
        <div className="bg-background relative mx-auto max-w-2xl pb-3 md:pb-12">
          <Fade bottom className="absolute inset-x-0 top-0 h-4 -translate-y-full" />
          <AgentControlBar
            controls={controls}
            isConnected={session.isConnected}
            onDisconnect={session.end}
            onChatOpenChange={setChatOpen}
          />
        </div>
      </MotionBottom>
    </section>
  );
};
