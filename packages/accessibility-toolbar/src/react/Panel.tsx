import { useId } from "react";
import type { ReactNode } from "react";

import {
  DEFAULT_SETTINGS,
  SETTING_LIMITS,
  type A11ySettings,
  type ProfileId,
  type SettableKey,
  type ThemeId,
} from "../core/settings";
import { Tip } from "./Tooltip";
import { useA11y } from "./useA11y";
import { useAnnounce } from "./useAnnounce";
import { useSpeech } from "./useSpeech";

const PROFILES: ReadonlyArray<{ id: ProfileId; label: string; description: string }> = [
  {
    id: "low-vision",
    label: "Low vision",
    description:
      "Text at 150%, white-on-black high contrast, underlined links, a thick focus outline, a large cursor and bigger click targets.",
  },
  {
    id: "dyslexia",
    label: "Dyslexia",
    description:
      "The OpenDyslexic font with wider letter, word and line spacing, and a narrower reading width.",
  },
  {
    id: "adhd-focus",
    label: "ADHD / focus",
    description: "Calmer motion, a thick focus outline and a narrower reading width, to cut distraction.",
  },
  {
    id: "motor-impairment",
    label: "Motor",
    description:
      "Bigger click targets, a large cursor and a thick focus outline, for anyone who finds precise pointing hard.",
  },
  {
    id: "epilepsy-safe",
    label: "Photosensitive",
    description:
      "Stops animation, mutes audio and video, and softens colours. It can't detect flashing inside videos or images.",
  },
  {
    id: "older-users",
    label: "Older users",
    description: "Text at 130% with more line spacing, underlined links, bigger targets and gentler motion.",
  },
  {
    id: "protanopia",
    label: "Protanopia",
    description: "Shifts colours so reds are easier to tell apart, for red-weak colour vision. Also underlines links.",
  },
  {
    id: "deuteranopia",
    label: "Deuteranopia",
    description:
      "Shifts colours so greens are easier to tell apart, for green-weak colour vision. Also underlines links.",
  },
  {
    id: "tritanopia",
    label: "Tritanopia",
    description: "Shifts colours so blues and yellows are easier to tell apart. Also underlines links.",
  },
];

const THEMES: ReadonlyArray<{ id: ThemeId; label: string; description: string }> = [
  { id: "default", label: "Default", description: "The site's own colours." },
  {
    id: "contrast-dark",
    label: "High contrast dark",
    description:
      "White text on black with yellow links. The strongest contrast; it replaces the site's own colours.",
  },
  {
    id: "contrast-light",
    label: "High contrast light",
    description: "Black text on white with dark blue links. Replaces the site's own colours.",
  },
  {
    id: "monochrome",
    label: "Monochrome",
    description: "Removes all colour from the page, for anyone colour distracts.",
  },
  { id: "saturation-low", label: "Soft colours", description: "Tones every colour down to half strength." },
  { id: "saturation-high", label: "Vivid colours", description: "Makes colours stronger and easier to tell apart." },
  { id: "invert", label: "Invert", description: "Swaps light and dark. Photos and videos keep their real colours." },
];

const FONTS: ReadonlyArray<{ id: A11ySettings["fontFamily"]; label: string; description: string }> = [
  { id: "default", label: "Default", description: "The site's own font." },
  {
    id: "readable",
    label: "Readable",
    description:
      "Atkinson Hyperlegible, designed by the Braille Institute so similar characters like I, l and 1 are easy to tell apart.",
  },
  {
    id: "dyslexic",
    label: "Dyslexia",
    description:
      "OpenDyslexic, with weighted letter shapes some dyslexic readers find easier. Evidence is mixed, so try it with the spacing controls too.",
  },
];

const CURSORS: ReadonlyArray<{ id: A11ySettings["cursor"]; label: string; description: string }> = [
  { id: "default", label: "Default", description: "Your normal mouse pointer." },
  {
    id: "large-black",
    label: "Large dark",
    description: "A large black pointer with a white outline, for light pages.",
  },
  {
    id: "large-white",
    label: "Large light",
    description: "A large white pointer with a black outline, for dark or high-contrast pages.",
  },
];

const SECTION_KEYS = {
  reading: ["tts"],
  colour: ["theme", "customColors"],
  text: ["fontScale", "lineHeight", "letterSpacing", "wordSpacing", "fontFamily", "contentWidth"],
  navigation: ["highlight", "enlargeTargets", "cursor"],
  motion: ["motion", "muteMedia"],
} as const satisfies Record<string, readonly SettableKey[]>;

function isDefault(settings: Readonly<A11ySettings>, keys: readonly SettableKey[]): boolean {
  return keys.every((key) => JSON.stringify(settings[key]) === JSON.stringify(DEFAULT_SETTINGS[key]));
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function round(value: number, step: number): number {
  return Math.round(value / step) * step;
}

function Section({
  title,
  resetLabel,
  canReset,
  onReset,
  children,
}: {
  title: string;
  resetLabel: string;
  canReset: boolean;
  onReset: () => void;
  children: ReactNode;
}) {
  return (
    <fieldset>
      <legend>{title}</legend>
      <Tip
        className="section-reset"
        label={
          canReset
            ? `Undo the changes in ${title}. Nothing else is affected.`
            : `Nothing in ${title} has been changed.`
        }
      >
        <button
          type="button"
          className="reset-btn"
          aria-disabled={!canReset}
          onClick={() => {
            if (canReset) onReset();
          }}
        >
          {resetLabel}
        </button>
      </Tip>
      <div className="section-body">{children}</div>
    </fieldset>
  );
}

function CheckboxRow({
  label,
  tip,
  checked,
  disabled = false,
  onChange,
}: {
  label: string;
  tip: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
}) {
  const id = useId();
  return (
    <div className="row">
      <label htmlFor={id}>{label}</label>
      <Tip label={tip}>
        <input
          id={id}
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
        />
      </Tip>
    </div>
  );
}

function RangeRow({
  label,
  tip,
  value,
  valueText,
  min,
  max,
  step,
  onChange,
  stepper = false,
}: {
  label: string;
  tip: string;
  value: number;
  valueText: string;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  stepper?: boolean;
}) {
  const id = useId();
  const nudge = (direction: 1 | -1) =>
    onChange(Math.min(max, Math.max(min, round(value + direction * step, step))));
  const slider = (
    <Tip label={tip} block>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        aria-valuetext={valueText}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </Tip>
  );

  return (
    <div className="range-row">
      <label htmlFor={id}>
        <span>{label}</span>
        <span className="value" aria-hidden="true">
          {valueText}
        </span>
      </label>
      {stepper ? (
        <div className="stepper">
          <Tip label={`Decrease ${label.toLowerCase()} by one step`}>
            <button type="button" className="step-btn" aria-disabled={value <= min} onClick={() => nudge(-1)}>
              Smaller
            </button>
          </Tip>
          {slider}
          <Tip label={`Increase ${label.toLowerCase()} by one step`}>
            <button type="button" className="step-btn" aria-disabled={value >= max} onClick={() => nudge(1)}>
              Bigger
            </button>
          </Tip>
        </div>
      ) : (
        slider
      )}
    </div>
  );
}

function ChoiceGroup<T extends string>({
  labelledBy,
  options,
  selected,
  onSelect,
  columns = 2,
}: {
  labelledBy?: string;
  options: ReadonlyArray<{ id: T; label: string; description: string }>;
  selected: T | null;
  onSelect: (id: T, label: string) => void;
  columns?: 2 | 3;
}) {
  return (
    <div
      role={labelledBy ? "group" : undefined}
      aria-labelledby={labelledBy}
      className={`grid grid-${columns}`}
    >
      {options.map((option) => (
        <Tip key={option.id} label={option.description} block>
          <button
            type="button"
            className="choice"
            aria-pressed={selected === option.id}
            onClick={() => onSelect(option.id, option.label)}
          >
            {option.label}
          </button>
        </Tip>
      ))}
    </div>
  );
}

function VoiceSelect({
  voices,
  value,
  onChange,
}: {
  voices: ReadonlyArray<{ uri: string; name: string; lang: string }>;
  value: string | null;
  onChange: (voiceURI: string | null) => void;
}) {
  const id = useId();
  return (
    <div className="range-row">
      <label htmlFor={id}>
        <span>Voice</span>
      </label>
      <Tip label="Voices come from your browser and operating system, so the list differs between devices." block>
        <select id={id} value={value ?? ""} onChange={(event) => onChange(event.target.value || null)}>
          <option value="">Browser default</option>
          {voices.map((voice) => (
            <option key={voice.uri} value={voice.uri}>
              {voice.name} ({voice.lang})
            </option>
          ))}
        </select>
      </Tip>
    </div>
  );
}

export function Panel() {
  const announce = useAnnounce();
  const { value: settings, set, applyProfile, clearProfile, resetKeys } = useA11y();
  const speech = useSpeech();
  const fontLabelId = useId();
  const cursorLabelId = useId();
  const speaking = speech.status !== "idle";
  const pageLanguage = document.documentElement.lang.slice(0, 2).toLowerCase() || "en";
  const voices = [...speech.voices].sort((a, b) => {
    const rank = (voice: { lang: string }) => (voice.lang.toLowerCase().startsWith(pageLanguage) ? 0 : 1);
    return rank(a) - rank(b) || a.name.localeCompare(b.name);
  });

  const resetSection = (title: string, keys: readonly SettableKey[]) => {
    resetKeys(keys);
    announce(`${title} reset to default`);
  };

  return (
    <div className="panel-body">
      <Section
        title="Profiles"
        resetLabel="Reset profile"
        canReset={settings.profile !== null}
        onReset={() => {
          clearProfile();
          announce("Profile turned off. Your earlier settings are back.");
        }}
      >
        <p className="hint">
          A profile changes several settings at once. Choose it again, or press Reset profile, to undo
          it and get back the settings you had before.
        </p>
        <ChoiceGroup
          options={PROFILES}
          selected={settings.profile}
          onSelect={(id, label) => {
            const turningOff = settings.profile === id;
            applyProfile(id);
            announce(turningOff ? `${label} profile turned off` : `${label} profile on`);
          }}
        />
      </Section>

      <Section
        title="Read aloud"
        resetLabel="Reset reading"
        canReset={!isDefault(settings, SECTION_KEYS.reading)}
        onReset={() => {
          speech.stop();
          resetSection("Read aloud", SECTION_KEYS.reading);
        }}
      >
        {speech.supported ? (
          <>
            <div className="button-row">
              <Tip label="Reads the main content of this page aloud from the top, highlighting each sentence as it goes.">
                <button type="button" className="action-btn" onClick={() => speech.speakPage()}>
                  Read page
                </button>
              </Tip>
              <Tip
                label={
                  speech.hasSelection
                    ? "Reads the text you selected on the page."
                    : "Select some text on the page first, then press this to hear just that."
                }
              >
                <button
                  type="button"
                  className="action-btn"
                  aria-disabled={!speech.hasSelection}
                  onClick={() => {
                    if (!speech.speakSelection()) announce("Select some text on the page first");
                  }}
                >
                  Read selection
                </button>
              </Tip>
              {speech.status === "paused" ? (
                <Tip label="Carry on reading from where it paused.">
                  <button type="button" className="action-btn" onClick={speech.resume}>
                    Resume
                  </button>
                </Tip>
              ) : (
                <Tip label="Pause reading. Resume carries on from the same place.">
                  <button
                    type="button"
                    className="action-btn"
                    aria-disabled={speech.status !== "speaking"}
                    onClick={speech.pause}
                  >
                    Pause
                  </button>
                </Tip>
              )}
              <Tip label="Stop reading and clear the highlight.">
                <button type="button" className="action-btn" aria-disabled={!speaking} onClick={speech.stop}>
                  Stop
                </button>
              </Tip>
            </div>
            <p className="status-line">
              {speech.status === "speaking" ? "Reading aloud…" : speech.status === "paused" ? "Paused" : "Not reading"}
            </p>
            <CheckboxRow
              label="Read text when I click it"
              tip="Click any paragraph, heading or list item to hear it. When you Tab onto a button or link, its name is read too."
              checked={settings.tts.enabled}
              onChange={(enabled) => {
                set("tts", { ...settings.tts, enabled });
                announce(enabled ? "Click to read is on" : "Click to read is off");
              }}
            />
            <CheckboxRow
              label="Highlight words as they're read"
              tip={
                speech.highlightSupported
                  ? "Marks the sentence and the word being spoken, so you can follow along."
                  : "This browser can't highlight text without changing the page, so reading works without it."
              }
              checked={settings.tts.highlight && speech.highlightSupported}
              disabled={!speech.highlightSupported}
              onChange={(highlight) => set("tts", { ...settings.tts, highlight })}
            />
            <RangeRow
              label="Reading speed"
              tip="How fast the voice reads. 1× is normal; a change applies from the next sentence."
              value={settings.tts.rate}
              valueText={`${settings.tts.rate.toFixed(1)}×`}
              min={SETTING_LIMITS.rate.min}
              max={SETTING_LIMITS.rate.max}
              step={0.1}
              onChange={(rate) => {
                set("tts", { ...settings.tts, rate });
                announce(`Reading speed ${rate.toFixed(1)} times`);
              }}
            />
            <VoiceSelect
              voices={voices}
              value={settings.tts.voiceURI}
              onChange={(voiceURI) => set("tts", { ...settings.tts, voiceURI })}
            />
          </>
        ) : (
          <p className="note">This browser can&apos;t read text aloud.</p>
        )}
      </Section>

      <Section
        title="Colour and contrast"
        resetLabel="Reset colours"
        canReset={!isDefault(settings, SECTION_KEYS.colour)}
        onReset={() => resetSection("Colour and contrast", SECTION_KEYS.colour)}
      >
        <ChoiceGroup
          options={THEMES}
          selected={settings.theme}
          onSelect={(id, label) => {
            set("theme", id);
            announce(id === "default" ? "Site colours restored" : `${label} on`);
          }}
        />
      </Section>

      <Section
        title="Text"
        resetLabel="Reset text"
        canReset={!isDefault(settings, SECTION_KEYS.text)}
        onReset={() => resetSection("Text", SECTION_KEYS.text)}
      >
        <RangeRow
          label="Text size"
          tip="Scales every piece of text on the page, from 100% to 200%. Layout grows with it, the way browser text zoom does."
          value={settings.fontScale}
          valueText={percent(settings.fontScale)}
          min={SETTING_LIMITS.fontScale.min}
          max={SETTING_LIMITS.fontScale.max}
          step={0.1}
          stepper
          onChange={(fontScale) => {
            set("fontScale", fontScale);
            announce(`Text size ${percent(fontScale)}`);
          }}
        />
        <RangeRow
          label="Line height"
          tip="Adds space between lines of text, which makes long paragraphs easier to track."
          value={settings.lineHeight}
          valueText={settings.lineHeight.toFixed(1)}
          min={SETTING_LIMITS.lineHeight.min}
          max={SETTING_LIMITS.lineHeight.max}
          step={0.1}
          onChange={(lineHeight) => {
            set("lineHeight", lineHeight);
            announce(`Line height ${lineHeight.toFixed(1)}`);
          }}
        />
        <RangeRow
          label="Letter spacing"
          tip="Adds space between letters, which can stop them seeming to crowd or swap places."
          value={settings.letterSpacing}
          valueText={`${settings.letterSpacing.toFixed(2)} em`}
          min={SETTING_LIMITS.letterSpacing.min}
          max={SETTING_LIMITS.letterSpacing.max}
          step={0.02}
          onChange={(letterSpacing) => {
            set("letterSpacing", letterSpacing);
            announce(`Letter spacing ${letterSpacing.toFixed(2)} em`);
          }}
        />
        <RangeRow
          label="Word spacing"
          tip="Adds space between words, so each word stands on its own."
          value={settings.wordSpacing}
          valueText={`${settings.wordSpacing.toFixed(2)} em`}
          min={SETTING_LIMITS.wordSpacing.min}
          max={SETTING_LIMITS.wordSpacing.max}
          step={0.05}
          onChange={(wordSpacing) => {
            set("wordSpacing", wordSpacing);
            announce(`Word spacing ${wordSpacing.toFixed(2)} em`);
          }}
        />
        <p className="group-label" id={fontLabelId}>
          Font
        </p>
        <ChoiceGroup
          labelledBy={fontLabelId}
          columns={3}
          options={FONTS}
          selected={settings.fontFamily}
          onSelect={(id, label) => {
            set("fontFamily", id);
            announce(`${label} font`);
          }}
        />
        <CheckboxRow
          label="Narrow reading width"
          tip="Keeps paragraphs to about 68 characters per line, which is easier to follow from one line to the next."
          checked={settings.contentWidth === "narrow"}
          onChange={(narrow) => set("contentWidth", narrow ? "narrow" : "default")}
        />
      </Section>

      <Section
        title="Navigation"
        resetLabel="Reset navigation"
        canReset={!isDefault(settings, SECTION_KEYS.navigation)}
        onReset={() => resetSection("Navigation", SECTION_KEYS.navigation)}
      >
        <CheckboxRow
          label="Underline links"
          tip="Underlines every link, so you can find links without relying on their colour."
          checked={settings.highlight.links}
          onChange={(links) => set("highlight", { ...settings.highlight, links })}
        />
        <CheckboxRow
          label="Outline headings"
          tip="Draws a dashed outline round each heading, to show how the page is organised."
          checked={settings.highlight.headings}
          onChange={(headings) => set("highlight", { ...settings.highlight, headings })}
        />
        <CheckboxRow
          label="Thick focus outline"
          tip="Shows a thick orange outline around whatever keyboard focus is on, so you never lose your place."
          checked={settings.highlight.focus}
          onChange={(focus) => set("highlight", { ...settings.highlight, focus })}
        />
        <CheckboxRow
          label="Highlight on hover"
          tip="Outlines the link, button or field under the mouse pointer."
          checked={settings.highlight.hover}
          onChange={(hover) => set("highlight", { ...settings.highlight, hover })}
        />
        <CheckboxRow
          label="Bigger click targets"
          tip="Makes buttons and form fields at least 44 by 44 pixels, and checkboxes larger, so they're easier to hit."
          checked={settings.enlargeTargets}
          onChange={(enlargeTargets) => set("enlargeTargets", enlargeTargets)}
        />
        <p className="group-label" id={cursorLabelId}>
          Cursor
        </p>
        <ChoiceGroup
          labelledBy={cursorLabelId}
          columns={3}
          options={CURSORS}
          selected={settings.cursor}
          onSelect={(id, label) => {
            set("cursor", id);
            announce(`${label} cursor`);
          }}
        />
      </Section>

      <Section
        title="Motion and media"
        resetLabel="Reset motion"
        canReset={!isDefault(settings, SECTION_KEYS.motion)}
        onReset={() => resetSection("Motion and media", SECTION_KEYS.motion)}
      >
        <CheckboxRow
          label="Stop animations"
          tip="Turns off animations, transitions and smooth scrolling on this site."
          checked={settings.motion === "off"}
          onChange={(off) => {
            set("motion", off ? "off" : "default");
            announce(off ? "Animations stopped" : "Animations restored");
          }}
        />
        <CheckboxRow
          label="Mute audio and video"
          tip="Mutes every audio and video player on the page, including any that load later."
          checked={settings.muteMedia}
          onChange={(muteMedia) => set("muteMedia", muteMedia)}
        />
      </Section>
    </div>
  );
}
