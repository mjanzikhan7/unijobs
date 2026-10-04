import { useAnnounce, useA11y, useSpeech, Tip } from './chunk-VDQ2JXBJ.js';
import { SETTING_LIMITS, DEFAULT_SETTINGS } from './chunk-S7H7F2SZ.js';
import { useId } from 'react';
import { jsxs, jsx, Fragment } from 'react/jsx-runtime';

var PROFILES = [
  {
    id: "low-vision",
    label: "Low vision",
    description: "Text at 150%, white-on-black high contrast, underlined links, a thick focus outline, a large cursor and bigger click targets."
  },
  {
    id: "dyslexia",
    label: "Dyslexia",
    description: "The OpenDyslexic font with wider letter, word and line spacing, and a narrower reading width."
  },
  {
    id: "adhd-focus",
    label: "ADHD / focus",
    description: "Calmer motion, a thick focus outline and a narrower reading width, to cut distraction."
  },
  {
    id: "motor-impairment",
    label: "Motor",
    description: "Bigger click targets, a large cursor and a thick focus outline, for anyone who finds precise pointing hard."
  },
  {
    id: "epilepsy-safe",
    label: "Photosensitive",
    description: "Stops animation, mutes audio and video, and softens colours. It can't detect flashing inside videos or images."
  },
  {
    id: "older-users",
    label: "Older users",
    description: "Text at 130% with more line spacing, underlined links, bigger targets and gentler motion."
  },
  {
    id: "protanopia",
    label: "Protanopia",
    description: "Shifts colours so reds are easier to tell apart, for red-weak colour vision. Also underlines links."
  },
  {
    id: "deuteranopia",
    label: "Deuteranopia",
    description: "Shifts colours so greens are easier to tell apart, for green-weak colour vision. Also underlines links."
  },
  {
    id: "tritanopia",
    label: "Tritanopia",
    description: "Shifts colours so blues and yellows are easier to tell apart. Also underlines links."
  }
];
var THEMES = [
  { id: "default", label: "Default", description: "The site's own colours." },
  {
    id: "contrast-dark",
    label: "High contrast dark",
    description: "White text on black with yellow links. The strongest contrast; it replaces the site's own colours."
  },
  {
    id: "contrast-light",
    label: "High contrast light",
    description: "Black text on white with dark blue links. Replaces the site's own colours."
  },
  {
    id: "monochrome",
    label: "Monochrome",
    description: "Removes all colour from the page, for anyone colour distracts."
  },
  { id: "saturation-low", label: "Soft colours", description: "Tones every colour down to half strength." },
  { id: "saturation-high", label: "Vivid colours", description: "Makes colours stronger and easier to tell apart." },
  { id: "invert", label: "Invert", description: "Swaps light and dark. Photos and videos keep their real colours." }
];
var FONTS = [
  { id: "default", label: "Default", description: "The site's own font." },
  {
    id: "readable",
    label: "Readable",
    description: "Atkinson Hyperlegible, designed by the Braille Institute so similar characters like I, l and 1 are easy to tell apart."
  },
  {
    id: "dyslexic",
    label: "Dyslexia",
    description: "OpenDyslexic, with weighted letter shapes some dyslexic readers find easier. Evidence is mixed, so try it with the spacing controls too."
  }
];
var CURSORS = [
  { id: "default", label: "Default", description: "Your normal mouse pointer." },
  {
    id: "large-black",
    label: "Large dark",
    description: "A large black pointer with a white outline, for light pages."
  },
  {
    id: "large-white",
    label: "Large light",
    description: "A large white pointer with a black outline, for dark or high-contrast pages."
  }
];
var SECTION_KEYS = {
  reading: ["tts"],
  colour: ["theme", "customColors"],
  text: ["fontScale", "lineHeight", "letterSpacing", "wordSpacing", "fontFamily", "contentWidth"],
  navigation: ["highlight", "enlargeTargets", "cursor"],
  motion: ["motion", "muteMedia"]
};
function isDefault(settings, keys) {
  return keys.every((key) => JSON.stringify(settings[key]) === JSON.stringify(DEFAULT_SETTINGS[key]));
}
function percent(value) {
  return `${Math.round(value * 100)}%`;
}
function round(value, step) {
  return Math.round(value / step) * step;
}
function Section({
  title,
  resetLabel,
  canReset,
  onReset,
  children
}) {
  return /* @__PURE__ */ jsxs("fieldset", { children: [
    /* @__PURE__ */ jsx("legend", { children: title }),
    /* @__PURE__ */ jsx(
      Tip,
      {
        className: "section-reset",
        label: canReset ? `Undo the changes in ${title}. Nothing else is affected.` : `Nothing in ${title} has been changed.`,
        children: /* @__PURE__ */ jsx(
          "button",
          {
            type: "button",
            className: "reset-btn",
            "aria-disabled": !canReset,
            onClick: () => {
              if (canReset) onReset();
            },
            children: resetLabel
          }
        )
      }
    ),
    /* @__PURE__ */ jsx("div", { className: "section-body", children })
  ] });
}
function CheckboxRow({
  label,
  tip,
  checked,
  disabled = false,
  onChange
}) {
  const id = useId();
  return /* @__PURE__ */ jsxs("div", { className: "row", children: [
    /* @__PURE__ */ jsx("label", { htmlFor: id, children: label }),
    /* @__PURE__ */ jsx(Tip, { label: tip, children: /* @__PURE__ */ jsx(
      "input",
      {
        id,
        type: "checkbox",
        checked,
        disabled,
        onChange: (event) => onChange(event.target.checked)
      }
    ) })
  ] });
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
  stepper = false
}) {
  const id = useId();
  const nudge = (direction) => onChange(Math.min(max, Math.max(min, round(value + direction * step, step))));
  const slider = /* @__PURE__ */ jsx(Tip, { label: tip, block: true, children: /* @__PURE__ */ jsx(
    "input",
    {
      id,
      type: "range",
      min,
      max,
      step,
      value,
      "aria-valuetext": valueText,
      onChange: (event) => onChange(Number(event.target.value))
    }
  ) });
  return /* @__PURE__ */ jsxs("div", { className: "range-row", children: [
    /* @__PURE__ */ jsxs("label", { htmlFor: id, children: [
      /* @__PURE__ */ jsx("span", { children: label }),
      /* @__PURE__ */ jsx("span", { className: "value", "aria-hidden": "true", children: valueText })
    ] }),
    stepper ? /* @__PURE__ */ jsxs("div", { className: "stepper", children: [
      /* @__PURE__ */ jsx(Tip, { label: `Decrease ${label.toLowerCase()} by one step`, children: /* @__PURE__ */ jsx("button", { type: "button", className: "step-btn", "aria-disabled": value <= min, onClick: () => nudge(-1), children: "Smaller" }) }),
      slider,
      /* @__PURE__ */ jsx(Tip, { label: `Increase ${label.toLowerCase()} by one step`, children: /* @__PURE__ */ jsx("button", { type: "button", className: "step-btn", "aria-disabled": value >= max, onClick: () => nudge(1), children: "Bigger" }) })
    ] }) : slider
  ] });
}
function ChoiceGroup({
  labelledBy,
  options,
  selected,
  onSelect,
  columns = 2
}) {
  return /* @__PURE__ */ jsx(
    "div",
    {
      role: labelledBy ? "group" : void 0,
      "aria-labelledby": labelledBy,
      className: `grid grid-${columns}`,
      children: options.map((option) => /* @__PURE__ */ jsx(Tip, { label: option.description, block: true, children: /* @__PURE__ */ jsx(
        "button",
        {
          type: "button",
          className: "choice",
          "aria-pressed": selected === option.id,
          onClick: () => onSelect(option.id, option.label),
          children: option.label
        }
      ) }, option.id))
    }
  );
}
function VoiceSelect({
  voices,
  value,
  onChange
}) {
  const id = useId();
  return /* @__PURE__ */ jsxs("div", { className: "range-row", children: [
    /* @__PURE__ */ jsx("label", { htmlFor: id, children: /* @__PURE__ */ jsx("span", { children: "Voice" }) }),
    /* @__PURE__ */ jsx(Tip, { label: "Voices come from your browser and operating system, so the list differs between devices.", block: true, children: /* @__PURE__ */ jsxs("select", { id, value: value ?? "", onChange: (event) => onChange(event.target.value || null), children: [
      /* @__PURE__ */ jsx("option", { value: "", children: "Browser default" }),
      voices.map((voice) => /* @__PURE__ */ jsxs("option", { value: voice.uri, children: [
        voice.name,
        " (",
        voice.lang,
        ")"
      ] }, voice.uri))
    ] }) })
  ] });
}
function Panel() {
  const announce = useAnnounce();
  const { value: settings, set, applyProfile, clearProfile, resetKeys } = useA11y();
  const speech = useSpeech();
  const fontLabelId = useId();
  const cursorLabelId = useId();
  const speaking = speech.status !== "idle";
  const pageLanguage = document.documentElement.lang.slice(0, 2).toLowerCase() || "en";
  const voices = [...speech.voices].sort((a, b) => {
    const rank = (voice) => voice.lang.toLowerCase().startsWith(pageLanguage) ? 0 : 1;
    return rank(a) - rank(b) || a.name.localeCompare(b.name);
  });
  const resetSection = (title, keys) => {
    resetKeys(keys);
    announce(`${title} reset to default`);
  };
  return /* @__PURE__ */ jsxs("div", { className: "panel-body", children: [
    /* @__PURE__ */ jsxs(
      Section,
      {
        title: "Profiles",
        resetLabel: "Reset profile",
        canReset: settings.profile !== null,
        onReset: () => {
          clearProfile();
          announce("Profile turned off. Your earlier settings are back.");
        },
        children: [
          /* @__PURE__ */ jsx("p", { className: "hint", children: "A profile changes several settings at once. Choose it again, or press Reset profile, to undo it and get back the settings you had before." }),
          /* @__PURE__ */ jsx(
            ChoiceGroup,
            {
              options: PROFILES,
              selected: settings.profile,
              onSelect: (id, label) => {
                const turningOff = settings.profile === id;
                applyProfile(id);
                announce(turningOff ? `${label} profile turned off` : `${label} profile on`);
              }
            }
          )
        ]
      }
    ),
    /* @__PURE__ */ jsx(
      Section,
      {
        title: "Read aloud",
        resetLabel: "Reset reading",
        canReset: !isDefault(settings, SECTION_KEYS.reading),
        onReset: () => {
          speech.stop();
          resetSection("Read aloud", SECTION_KEYS.reading);
        },
        children: speech.supported ? /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsxs("div", { className: "button-row", children: [
            /* @__PURE__ */ jsx(Tip, { label: "Reads the main content of this page aloud from the top, highlighting each sentence as it goes.", children: /* @__PURE__ */ jsx("button", { type: "button", className: "action-btn", onClick: () => speech.speakPage(), children: "Read page" }) }),
            /* @__PURE__ */ jsx(
              Tip,
              {
                label: speech.hasSelection ? "Reads the text you selected on the page." : "Select some text on the page first, then press this to hear just that.",
                children: /* @__PURE__ */ jsx(
                  "button",
                  {
                    type: "button",
                    className: "action-btn",
                    "aria-disabled": !speech.hasSelection,
                    onClick: () => {
                      if (!speech.speakSelection()) announce("Select some text on the page first");
                    },
                    children: "Read selection"
                  }
                )
              }
            ),
            speech.status === "paused" ? /* @__PURE__ */ jsx(Tip, { label: "Carry on reading from where it paused.", children: /* @__PURE__ */ jsx("button", { type: "button", className: "action-btn", onClick: speech.resume, children: "Resume" }) }) : /* @__PURE__ */ jsx(Tip, { label: "Pause reading. Resume carries on from the same place.", children: /* @__PURE__ */ jsx(
              "button",
              {
                type: "button",
                className: "action-btn",
                "aria-disabled": speech.status !== "speaking",
                onClick: speech.pause,
                children: "Pause"
              }
            ) }),
            /* @__PURE__ */ jsx(Tip, { label: "Stop reading and clear the highlight.", children: /* @__PURE__ */ jsx("button", { type: "button", className: "action-btn", "aria-disabled": !speaking, onClick: speech.stop, children: "Stop" }) })
          ] }),
          /* @__PURE__ */ jsx("p", { className: "status-line", children: speech.status === "speaking" ? "Reading aloud\u2026" : speech.status === "paused" ? "Paused" : "Not reading" }),
          /* @__PURE__ */ jsx(
            CheckboxRow,
            {
              label: "Read text when I click it",
              tip: "Click any paragraph, heading or list item to hear it. When you Tab onto a button or link, its name is read too.",
              checked: settings.tts.enabled,
              onChange: (enabled) => {
                set("tts", { ...settings.tts, enabled });
                announce(enabled ? "Click to read is on" : "Click to read is off");
              }
            }
          ),
          /* @__PURE__ */ jsx(
            CheckboxRow,
            {
              label: "Highlight words as they're read",
              tip: speech.highlightSupported ? "Marks the sentence and the word being spoken, so you can follow along." : "This browser can't highlight text without changing the page, so reading works without it.",
              checked: settings.tts.highlight && speech.highlightSupported,
              disabled: !speech.highlightSupported,
              onChange: (highlight) => set("tts", { ...settings.tts, highlight })
            }
          ),
          /* @__PURE__ */ jsx(
            RangeRow,
            {
              label: "Reading speed",
              tip: "How fast the voice reads. 1\xD7 is normal; a change applies from the next sentence.",
              value: settings.tts.rate,
              valueText: `${settings.tts.rate.toFixed(1)}\xD7`,
              min: SETTING_LIMITS.rate.min,
              max: SETTING_LIMITS.rate.max,
              step: 0.1,
              onChange: (rate) => {
                set("tts", { ...settings.tts, rate });
                announce(`Reading speed ${rate.toFixed(1)} times`);
              }
            }
          ),
          /* @__PURE__ */ jsx(
            VoiceSelect,
            {
              voices,
              value: settings.tts.voiceURI,
              onChange: (voiceURI) => set("tts", { ...settings.tts, voiceURI })
            }
          )
        ] }) : /* @__PURE__ */ jsx("p", { className: "note", children: "This browser can't read text aloud." })
      }
    ),
    /* @__PURE__ */ jsx(
      Section,
      {
        title: "Colour and contrast",
        resetLabel: "Reset colours",
        canReset: !isDefault(settings, SECTION_KEYS.colour),
        onReset: () => resetSection("Colour and contrast", SECTION_KEYS.colour),
        children: /* @__PURE__ */ jsx(
          ChoiceGroup,
          {
            options: THEMES,
            selected: settings.theme,
            onSelect: (id, label) => {
              set("theme", id);
              announce(id === "default" ? "Site colours restored" : `${label} on`);
            }
          }
        )
      }
    ),
    /* @__PURE__ */ jsxs(
      Section,
      {
        title: "Text",
        resetLabel: "Reset text",
        canReset: !isDefault(settings, SECTION_KEYS.text),
        onReset: () => resetSection("Text", SECTION_KEYS.text),
        children: [
          /* @__PURE__ */ jsx(
            RangeRow,
            {
              label: "Text size",
              tip: "Scales every piece of text on the page, from 100% to 200%. Layout grows with it, the way browser text zoom does.",
              value: settings.fontScale,
              valueText: percent(settings.fontScale),
              min: SETTING_LIMITS.fontScale.min,
              max: SETTING_LIMITS.fontScale.max,
              step: 0.1,
              stepper: true,
              onChange: (fontScale) => {
                set("fontScale", fontScale);
                announce(`Text size ${percent(fontScale)}`);
              }
            }
          ),
          /* @__PURE__ */ jsx(
            RangeRow,
            {
              label: "Line height",
              tip: "Adds space between lines of text, which makes long paragraphs easier to track.",
              value: settings.lineHeight,
              valueText: settings.lineHeight.toFixed(1),
              min: SETTING_LIMITS.lineHeight.min,
              max: SETTING_LIMITS.lineHeight.max,
              step: 0.1,
              onChange: (lineHeight) => {
                set("lineHeight", lineHeight);
                announce(`Line height ${lineHeight.toFixed(1)}`);
              }
            }
          ),
          /* @__PURE__ */ jsx(
            RangeRow,
            {
              label: "Letter spacing",
              tip: "Adds space between letters, which can stop them seeming to crowd or swap places.",
              value: settings.letterSpacing,
              valueText: `${settings.letterSpacing.toFixed(2)} em`,
              min: SETTING_LIMITS.letterSpacing.min,
              max: SETTING_LIMITS.letterSpacing.max,
              step: 0.02,
              onChange: (letterSpacing) => {
                set("letterSpacing", letterSpacing);
                announce(`Letter spacing ${letterSpacing.toFixed(2)} em`);
              }
            }
          ),
          /* @__PURE__ */ jsx(
            RangeRow,
            {
              label: "Word spacing",
              tip: "Adds space between words, so each word stands on its own.",
              value: settings.wordSpacing,
              valueText: `${settings.wordSpacing.toFixed(2)} em`,
              min: SETTING_LIMITS.wordSpacing.min,
              max: SETTING_LIMITS.wordSpacing.max,
              step: 0.05,
              onChange: (wordSpacing) => {
                set("wordSpacing", wordSpacing);
                announce(`Word spacing ${wordSpacing.toFixed(2)} em`);
              }
            }
          ),
          /* @__PURE__ */ jsx("p", { className: "group-label", id: fontLabelId, children: "Font" }),
          /* @__PURE__ */ jsx(
            ChoiceGroup,
            {
              labelledBy: fontLabelId,
              columns: 3,
              options: FONTS,
              selected: settings.fontFamily,
              onSelect: (id, label) => {
                set("fontFamily", id);
                announce(`${label} font`);
              }
            }
          ),
          /* @__PURE__ */ jsx(
            CheckboxRow,
            {
              label: "Narrow reading width",
              tip: "Keeps paragraphs to about 68 characters per line, which is easier to follow from one line to the next.",
              checked: settings.contentWidth === "narrow",
              onChange: (narrow) => set("contentWidth", narrow ? "narrow" : "default")
            }
          )
        ]
      }
    ),
    /* @__PURE__ */ jsxs(
      Section,
      {
        title: "Navigation",
        resetLabel: "Reset navigation",
        canReset: !isDefault(settings, SECTION_KEYS.navigation),
        onReset: () => resetSection("Navigation", SECTION_KEYS.navigation),
        children: [
          /* @__PURE__ */ jsx(
            CheckboxRow,
            {
              label: "Underline links",
              tip: "Underlines every link, so you can find links without relying on their colour.",
              checked: settings.highlight.links,
              onChange: (links) => set("highlight", { ...settings.highlight, links })
            }
          ),
          /* @__PURE__ */ jsx(
            CheckboxRow,
            {
              label: "Outline headings",
              tip: "Draws a dashed outline round each heading, to show how the page is organised.",
              checked: settings.highlight.headings,
              onChange: (headings) => set("highlight", { ...settings.highlight, headings })
            }
          ),
          /* @__PURE__ */ jsx(
            CheckboxRow,
            {
              label: "Thick focus outline",
              tip: "Shows a thick orange outline around whatever keyboard focus is on, so you never lose your place.",
              checked: settings.highlight.focus,
              onChange: (focus) => set("highlight", { ...settings.highlight, focus })
            }
          ),
          /* @__PURE__ */ jsx(
            CheckboxRow,
            {
              label: "Highlight on hover",
              tip: "Outlines the link, button or field under the mouse pointer.",
              checked: settings.highlight.hover,
              onChange: (hover) => set("highlight", { ...settings.highlight, hover })
            }
          ),
          /* @__PURE__ */ jsx(
            CheckboxRow,
            {
              label: "Bigger click targets",
              tip: "Makes buttons and form fields at least 44 by 44 pixels, and checkboxes larger, so they're easier to hit.",
              checked: settings.enlargeTargets,
              onChange: (enlargeTargets) => set("enlargeTargets", enlargeTargets)
            }
          ),
          /* @__PURE__ */ jsx("p", { className: "group-label", id: cursorLabelId, children: "Cursor" }),
          /* @__PURE__ */ jsx(
            ChoiceGroup,
            {
              labelledBy: cursorLabelId,
              columns: 3,
              options: CURSORS,
              selected: settings.cursor,
              onSelect: (id, label) => {
                set("cursor", id);
                announce(`${label} cursor`);
              }
            }
          )
        ]
      }
    ),
    /* @__PURE__ */ jsxs(
      Section,
      {
        title: "Motion and media",
        resetLabel: "Reset motion",
        canReset: !isDefault(settings, SECTION_KEYS.motion),
        onReset: () => resetSection("Motion and media", SECTION_KEYS.motion),
        children: [
          /* @__PURE__ */ jsx(
            CheckboxRow,
            {
              label: "Stop animations",
              tip: "Turns off animations, transitions and smooth scrolling on this site.",
              checked: settings.motion === "off",
              onChange: (off) => {
                set("motion", off ? "off" : "default");
                announce(off ? "Animations stopped" : "Animations restored");
              }
            }
          ),
          /* @__PURE__ */ jsx(
            CheckboxRow,
            {
              label: "Mute audio and video",
              tip: "Mutes every audio and video player on the page, including any that load later.",
              checked: settings.muteMedia,
              onChange: (muteMedia) => set("muteMedia", muteMedia)
            }
          )
        ]
      }
    )
  ] });
}

export { Panel };
//# sourceMappingURL=Panel-ATKMLKCH.js.map
//# sourceMappingURL=Panel-ATKMLKCH.js.map