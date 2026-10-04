import * as react from 'react';
import { ReactNode, RefObject, JSX, ReactElement } from 'react';
import { A as A11yEngineOptions, a as A11yEngine, b as A11ySettings, S as SettableKey, P as ProfileId, c as SpeechState } from '../engine-CSWYEqYM.js';

interface A11yContextValue {
    engine: A11yEngine;
    getSettings: () => Readonly<A11ySettings>;
    subscribe: (onChange: () => void) => () => void;
}
interface A11yProviderProps {
    children: ReactNode;
    options?: Omit<A11yEngineOptions, "announce">;
}
declare function A11yProvider({ children, options }: A11yProviderProps): react.JSX.Element;
declare function useA11yContext(): A11yContextValue;
declare function useA11ySnapshot(): Readonly<A11ySettings>;

interface UseA11yResult<T> {
    value: T;
    set: <K extends SettableKey>(key: K, value: A11ySettings[K]) => void;
    patch: (partial: Partial<Pick<A11ySettings, SettableKey>>) => void;
    applyProfile: (id: ProfileId) => void;
    clearProfile: () => void;
    resetKeys: (keys: readonly SettableKey[]) => void;
    reset: () => void;
}
declare function useA11y(): UseA11yResult<Readonly<A11ySettings>>;
declare function useA11y<T>(selector: (settings: Readonly<A11ySettings>) => T): UseA11yResult<T>;

declare function useAnnounce(): (message: string, politeness?: "polite" | "assertive") => void;

interface UseSpeechResult extends SpeechState {
    speakPage: (root?: Element | null) => boolean;
    speakSelection: () => boolean;
    speakText: (text: string) => boolean;
    pause: () => void;
    resume: () => void;
    stop: () => void;
}
declare function useSpeech(): UseSpeechResult;

interface UseRouteAnnouncerOptions {
    routeKey: string;
    title: string;
    focusTarget: RefObject<HTMLElement | null> | HTMLElement | null;
    suppress?: boolean;
}
declare function useRouteAnnouncer({ routeKey, title, focusTarget, suppress, }: UseRouteAnnouncerOptions): void;

declare function useFocusTrap(containerRef: RefObject<HTMLElement | null>, active: boolean): void;

declare function useRovingTabIndex(containerRef: RefObject<HTMLElement | null>, orientation?: "horizontal" | "vertical"): void;

declare function VisuallyHidden({ children, as: Component, }: {
    children: ReactNode;
    as?: keyof JSX.IntrinsicElements;
}): JSX.Element;

interface SkipLink {
    targetId: string;
    label: string;
}
interface SkipLinksProps {
    links: SkipLink[];
    className?: string;
}
declare function SkipLinks({ links, className }: SkipLinksProps): react.JSX.Element;

interface TipProps {
    label: string;
    children: ReactElement<{
        "aria-describedby"?: string;
    }>;
    block?: boolean;
    className?: string;
}
declare function Tip({ label, children, block, className }: TipProps): react.JSX.Element;

interface A11yToolbarProps {
    position?: "left" | "right";
    label?: string;
}
declare function A11yToolbar({ position, label }: A11yToolbarProps): react.JSX.Element | null;

export { A11yProvider, type A11yProviderProps, A11yToolbar, type A11yToolbarProps, type SkipLink, SkipLinks, type SkipLinksProps, Tip, type TipProps, type UseA11yResult, type UseRouteAnnouncerOptions, type UseSpeechResult, VisuallyHidden, useA11y, useA11yContext, useA11ySnapshot, useAnnounce, useFocusTrap, useRouteAnnouncer, useRovingTabIndex, useSpeech };
