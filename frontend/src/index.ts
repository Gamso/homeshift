import "./components/homeshift-card";

// Optional: register card metadata in the picker
(window as any).customCards = (window as any).customCards || [];
(window as any).customCards.push({
  type: "homeshift-card",
  name: "HomeShift Card",
  description:
    "Card to manage day mode and thermostat mode via the HomeShift integration.",
  preview: true,
});
