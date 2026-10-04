export interface MuteMediaController {
  start(): void;
  stop(): void;
}

export function createMuteMediaController(scope: Element = document.body): MuteMediaController {
  let observer: MutationObserver | null = null;

  function muteAll() {
    for (const el of scope.querySelectorAll<HTMLMediaElement>("video, audio")) {
      el.muted = true;
    }
  }

  return {
    start() {
      if (observer) return;
      muteAll();
      observer = new MutationObserver(muteAll);
      observer.observe(scope, { childList: true, subtree: true });
    },
    stop() {
      observer?.disconnect();
      observer = null;
    },
  };
}
