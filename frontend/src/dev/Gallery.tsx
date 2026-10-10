import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Drawer,
  EmptyState,
  ErrorBanner,
  Figure,
  InfoTip,
  LiveRegion,
  SectionHeader,
  SkipLink,
  StatusMark,
  VisuallyHidden,
} from "../components/ui";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-10">
      <h2 className="mb-4 border-b border-hairline pb-2 font-serif text-lg font-semibold text-ink">
        {title}
      </h2>
      <div className="flex flex-wrap gap-4">{children}</div>
    </section>
  );
}

export function Gallery() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [liveMsg, setLiveMsg] = useState("");

  return (
    <div className="min-h-screen bg-paper font-sans">
      <SkipLink />
      <main id="main-content" className="mx-auto max-w-[1280px] px-8 py-12">
        <h1 className="mb-8 font-serif text-2xl font-semibold text-ink">
          TalentLens — Component Gallery
        </h1>

        <Section title="Button">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="primary" disabled>Disabled</Button>
        </Section>

        <Section title="Badge">
          <Badge>Default</Badge>
          <Badge variant="accent">Accent</Badge>
          <Badge variant="red">High cost</Badge>
          <Badge variant="amber">Moderate cost</Badge>
          <Badge variant="green">Clear</Badge>
          <Badge variant="muted">Muted</Badge>
        </Section>

        <Section title="StatusMark">
          <StatusMark status="red" />
          <StatusMark status="amber" />
          <StatusMark status="green" />
        </Section>

        <Section title="Figure">
          <Figure value="₹18L" caption="Year-one cost, recommended mix" />
          <Figure value="89" caption="Option score out of 100" size="md" />
          <Figure value="62" unit="days" caption="Bengaluru Senior P50 time to fill" />
        </Section>

        <Section title="Card">
          <Card header={{ title: "Recommended mix", meaning: "Borrow Arjun + Build Priya" }}>
            <Figure value="₹18L" caption="Year-one cost" size="md" />
          </Card>
          <Card>
            <p className="text-sm text-muted">Card without header.</p>
          </Card>
        </Section>

        <Section title="SectionHeader">
          <SectionHeader>Default h2</SectionHeader>
          <SectionHeader as="h3" className="text-base">h3 variant</SectionHeader>
        </Section>

        <Section title="InfoTip">
          <InfoTip content="This is the tooltip / popover content. Hover, focus with keyboard, or tap to open." aria-label="More information">
            <span className="underline decoration-dotted cursor-help text-sm text-accent">
              Hover or click me
            </span>
          </InfoTip>
        </Section>

        <Section title="EmptyState">
          <div className="w-full">
            <EmptyState
              title="No analysis yet"
              description="Submit a requisition to begin."
            />
          </div>
        </Section>

        <Section title="ErrorBanner">
          <div className="w-full">
            <ErrorBanner message="Something went wrong. Please try again." />
          </div>
        </Section>

        <Section title="Drawer">
          <Button variant="secondary" onClick={() => setDrawerOpen(true)}>
            Open Drawer
          </Button>
          <Drawer
            open={drawerOpen}
            onOpenChange={setDrawerOpen}
            title="Example Drawer"
            description="Focus is trapped. Press Escape to close."
          >
            <p className="text-sm text-muted">Drawer content goes here.</p>
          </Drawer>
        </Section>

        <Section title="LiveRegion">
          <Button
            variant="secondary"
            onClick={() => setLiveMsg(`Update at ${new Date().toLocaleTimeString()}`)}
          >
            Trigger live announcement
          </Button>
          <LiveRegion>{liveMsg}</LiveRegion>
          <p className="w-full text-xs text-muted">
            (Screen readers will announce the message; sighted users see nothing.)
          </p>
        </Section>

        <Section title="VisuallyHidden">
          <span className="text-sm text-ink">
            Next to this text is hidden text for screen readers:{" "}
            <VisuallyHidden>This is only for screen readers.</VisuallyHidden>
            (end)
          </span>
        </Section>

        <Section title="Typography">
          <div className="w-full space-y-3">
            <p className="font-serif text-2xl font-semibold text-ink">
              Source Serif 4 — heading
            </p>
            <p className="font-sans text-base text-ink">
              IBM Plex Sans — interface text
            </p>
            <p className="font-mono text-base text-ink">
              IBM Plex Mono — ₹18L · 62 days · 89/100
            </p>
            <p className="font-sans text-sm text-muted">
              Muted text · secondary labels
            </p>
          </div>
        </Section>

        <Section title="Palette swatches">
          {[
            ["paper", "#FBFAF7"],
            ["surface", "#FFFFFF"],
            ["ink", "#1B1F2A"],
            ["muted", "#5B6170"],
            ["hairline", "#E4E1DA"],
            ["accent", "#1F3A5F"],
            ["redline", "#B42318"],
            ["amber", "#B54708"],
            ["green", "#067647"],
          ].map(([name, hex]) => (
            <div key={name} className="flex flex-col items-center gap-1">
              <div
                className="h-10 w-10 rounded border border-hairline"
                style={{ backgroundColor: hex }}
              />
              <span className="font-mono text-[10px] text-muted">{hex}</span>
              <span className="font-sans text-[10px] text-ink">{name}</span>
            </div>
          ))}
        </Section>
      </main>
    </div>
  );
}
