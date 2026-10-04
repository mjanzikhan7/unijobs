import { useCallback, useMemo, useSyncExternalStore } from "react";

import type { SpeechState } from "../core/speech";
import { useA11yContext } from "./A11yProvider";

export interface UseSpeechResult extends SpeechState {
  speakPage: (root?: Element | null) => boolean;
  speakSelection: () => boolean;
  speakText: (text: string) => boolean;
  pause: () => void;
  resume: () => void;
  stop: () => void;
}

export function useSpeech(): UseSpeechResult {
  const { engine } = useA11yContext();
  const speech = engine.speech;
  const subscribe = useCallback((onChange: () => void) => speech.subscribe(onChange), [speech]);
  const getState = useCallback(() => speech.state, [speech]);
  const state = useSyncExternalStore(subscribe, getState, getState);

  return useMemo(
    () => ({
      ...state,
      speakPage: (root?: Element | null) => speech.speakPage(root),
      speakSelection: () => speech.speakSelection(),
      speakText: (text: string) => speech.speakText(text),
      pause: () => speech.pause(),
      resume: () => speech.resume(),
      stop: () => speech.stop(),
    }),
    [state, speech],
  );
}
