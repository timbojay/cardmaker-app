const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, LevelFormat, ExternalHyperlink
} = require('docx');
const fs = require('fs');

// ── Colours ──────────────────────────────────────────────────────────────
const BLUE      = "1F4E79";
const BLUE_MID  = "2E75B6";
const BLUE_LITE = "D5E8F0";
const GREY_LITE = "F2F2F2";
const GREY_MID  = "D9D9D9";
const BLACK     = "1A1A1A";
const WHITE     = "FFFFFF";

// ── Helpers ───────────────────────────────────────────────────────────────
function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, font: "Arial", bold: true })],
    spacing: { before: 360, after: 120 },
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, font: "Arial", bold: true })],
    spacing: { before: 240, after: 80 },
  });
}

function heading3(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: "Arial", bold: true, size: 22, color: BLUE_MID })],
    spacing: { before: 200, after: 60 },
  });
}

function para(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, font: "Arial", size: opts.size || 22, color: opts.color || BLACK, bold: opts.bold || false, italics: opts.italic || false })],
    spacing: { before: opts.before || 80, after: opts.after || 80 },
    alignment: opts.align || AlignmentType.LEFT,
  });
}

function mixedPara(runs, opts = {}) {
  return new Paragraph({
    children: runs,
    spacing: { before: opts.before || 80, after: opts.after || 80 },
    alignment: opts.align || AlignmentType.LEFT,
  });
}

function run(text, opts = {}) {
  return new TextRun({ text, font: "Arial", size: opts.size || 22, color: opts.color || BLACK, bold: opts.bold || false, italics: opts.italic || false });
}

function bullet(text, opts = {}) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    children: [new TextRun({ text, font: "Arial", size: 22, color: opts.color || BLACK })],
    spacing: { before: 40, after: 40 },
  });
}

function spacer(lines = 1) {
  return Array.from({ length: lines }, () => new Paragraph({ children: [new TextRun("")], spacing: { before: 0, after: 0 } }));
}

// ── Table helpers ─────────────────────────────────────────────────────────
const cellBorder = { style: BorderStyle.SINGLE, size: 1, color: GREY_MID };
const allBorders = { top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder };

function headerCell(text, width) {
  return new TableCell({
    borders: allBorders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: BLUE_MID, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 140, right: 140 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: AlignmentType.LEFT,
      children: [new TextRun({ text, font: "Arial", bold: true, size: 20, color: WHITE })],
    })],
  });
}

function dataCell(text, width, shade = false, bold = false) {
  return new TableCell({
    borders: allBorders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: shade ? GREY_LITE : WHITE, type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 140, right: 140 },
    verticalAlign: VerticalAlign.TOP,
    children: [new Paragraph({
      children: [new TextRun({ text, font: "Arial", size: 20, color: BLACK, bold })],
    })],
  });
}

function codeCell(text, width) {
  return new TableCell({
    borders: allBorders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: "1E1E1E", type: ShadingType.CLEAR },
    margins: { top: 60, bottom: 60, left: 140, right: 140 },
    children: [new Paragraph({
      children: [new TextRun({ text, font: "Courier New", size: 18, color: "D4D4D4" })],
    })],
  });
}

// ── Callout box (single-row table used as shaded block) ───────────────────
function calloutBox(label, text, fillColor = BLUE_LITE) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders: {
              top:    { style: BorderStyle.THICK, size: 6, color: BLUE_MID },
              bottom: { style: BorderStyle.SINGLE, size: 1, color: GREY_MID },
              left:   { style: BorderStyle.THICK, size: 10, color: BLUE_MID },
              right:  { style: BorderStyle.SINGLE, size: 1, color: GREY_MID },
            },
            width: { size: 9360, type: WidthType.DXA },
            shading: { fill: fillColor, type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 160, right: 160 },
            children: [
              new Paragraph({ children: [new TextRun({ text: label, font: "Arial", bold: true, size: 20, color: BLUE })] }),
              new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 20, color: BLACK })], spacing: { before: 40 } }),
            ],
          }),
        ],
      }),
    ],
  });
}

// ── Pipeline step table ───────────────────────────────────────────────────
function pipelineTable(steps) {
  // steps: [{ num, title, desc }]
  const rows = steps.map((s, i) =>
    new TableRow({
      children: [
        new TableCell({
          borders: allBorders,
          width: { size: 780, type: WidthType.DXA },
          shading: { fill: BLUE_MID, type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 100, right: 100 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: s.num, font: "Arial", bold: true, size: 28, color: WHITE })] })],
        }),
        new TableCell({
          borders: allBorders,
          width: { size: 2400, type: WidthType.DXA },
          shading: { fill: i % 2 === 0 ? BLUE_LITE : WHITE, type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 140, right: 140 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ children: [new TextRun({ text: s.title, font: "Arial", bold: true, size: 20, color: BLUE })] })],
        }),
        new TableCell({
          borders: allBorders,
          width: { size: 6180, type: WidthType.DXA },
          shading: { fill: i % 2 === 0 ? BLUE_LITE : WHITE, type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 140, right: 140 },
          verticalAlign: VerticalAlign.TOP,
          children: [new Paragraph({ children: [new TextRun({ text: s.desc, font: "Arial", size: 20, color: BLACK })] })],
        }),
      ],
    })
  );

  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [780, 2400, 6180],
    rows,
  });
}

// ── Two-column key-value table ────────────────────────────────────────────
function kvTable(rows, col1 = 3120, col2 = 6240) {
  return new Table({
    width: { size: col1 + col2, type: WidthType.DXA },
    columnWidths: [col1, col2],
    rows: rows.map(([k, v], i) =>
      new TableRow({
        children: [
          dataCell(k, col1, true, true),
          dataCell(v, col2, false, false),
        ],
      })
    ),
  });
}

// ── Document ──────────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{
          level: 0,
          format: LevelFormat.BULLET,
          text: "\u2022",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: "Arial", size: 22, color: BLACK } },
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: BLUE },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE_MID, space: 1 } } },
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: BLUE_MID },
        paragraph: { spacing: { before: 280, after: 80 }, outlineLevel: 1 },
      },
    ],
  },

  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [
          new Paragraph({
            children: [
              new TextRun({ text: "Cardmaker App — Technical Overview", font: "Arial", size: 18, color: "888888" }),
              new TextRun({ text: "\tApril 2026", font: "Arial", size: 18, color: "888888" }),
            ],
            tabStops: [{ type: "right", position: 8640 }],
            border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: GREY_MID, space: 1 } },
          }),
        ],
      }),
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            children: [
              new TextRun({ text: "Space Junk — Private Project", font: "Arial", size: 16, color: "AAAAAA" }),
              new TextRun({ text: "\tPage ", font: "Arial", size: 16, color: "AAAAAA" }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "AAAAAA" }),
              new TextRun({ text: " of ", font: "Arial", size: 16, color: "AAAAAA" }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], font: "Arial", size: 16, color: "AAAAAA" }),
            ],
            tabStops: [{ type: "right", position: 8640 }],
            border: { top: { style: BorderStyle.SINGLE, size: 4, color: GREY_MID, space: 1 } },
          }),
        ],
      }),
    },

    children: [

      // ── Cover title ───────────────────────────────────────────────────
      new Paragraph({
        children: [new TextRun({ text: "Cardmaker App", font: "Arial", bold: true, size: 64, color: BLUE })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 480, after: 120 },
      }),
      new Paragraph({
        children: [new TextRun({ text: "Technical Overview", font: "Arial", size: 36, color: BLUE_MID })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 80 },
      }),
      new Paragraph({
        children: [new TextRun({ text: "Space Junk card game  |  April 2026", font: "Arial", size: 22, color: "888888", italics: true })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 480 },
      }),

      // ── Purpose ───────────────────────────────────────────────────────
      calloutBox(
        "What this app does",
        "Cardmaker is a full-stack local application that generates print-ready playing cards for the Space Junk card game. " +
        "It runs entirely on a 24 GB M4 MacBook Pro using a locally hosted AI image generation model — no cloud services or API keys are needed. " +
        "A React frontend lets you design cards, a Python/FastAPI backend manages data and orchestrates image generation, " +
        "and ComfyUI runs the AI model that draws the card art."
      ),
      ...spacer(1),

      // ── 1. Architecture ───────────────────────────────────────────────
      heading1("1. Architecture"),
      para(
        "The app has three layers running locally on the same machine. They communicate over HTTP on localhost."
      ),
      ...spacer(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 2160, 4800],
        rows: [
          new TableRow({
            children: [
              headerCell("Layer", 2400),
              headerCell("Technology", 2160),
              headerCell("Responsibility", 4800),
            ],
          }),
          new TableRow({
            children: [
              dataCell("Frontend", 2400, true, true),
              dataCell("React + Vite (TypeScript)", 2160, true),
              dataCell("Card editor UI — create, edit, preview cards and trigger generation", 4800, true),
            ],
          }),
          new TableRow({
            children: [
              dataCell("Backend API", 2400, false, true),
              dataCell("FastAPI (Python)", 2160),
              dataCell("REST API, SQLite database, card compositing, file management", 4800),
            ],
          }),
          new TableRow({
            children: [
              dataCell("Image Engine", 2400, true, true),
              dataCell("ComfyUI + FLUX model", 2160, true),
              dataCell("Receives generation requests over HTTP, runs the AI model, returns finished images", 4800, true),
            ],
          }),
        ],
      }),
      ...spacer(1),

      para("The frontend talks to the FastAPI backend on port 8000. The backend talks to ComfyUI on port 8188. All three run as separate processes on your MacBook.", { italic: true, color: "666666" }),
      ...spacer(1),

      // ── 2. Directory structure ─────────────────────────────────────────
      heading1("2. Directory Structure"),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3120, 6240],
        rows: [
          new TableRow({ children: [ headerCell("Path", 3120), headerCell("Contents", 6240) ] }),
          new TableRow({ children: [ dataCell("app/backend/", 3120, true, true), dataCell("FastAPI app — main.py, routers, services, database", 6240, true) ] }),
          new TableRow({ children: [ dataCell("app/backend/services/comfyui.py", 3120, false, true), dataCell("ComfyUI API client — builds prompts, queues jobs, retrieves images", 6240) ] }),
          new TableRow({ children: [ dataCell("app/backend/services/compositor.py", 3120, true, true), dataCell("Card compositing — assembles art, text, icons and border into one image", 6240, true) ] }),
          new TableRow({ children: [ dataCell("app/backend/routers/", 3120, false, true), dataCell("REST endpoints: cards, decks, card types, icons, backgrounds, export", 6240) ] }),
          new TableRow({ children: [ dataCell("app/frontend/", 3120, true, true), dataCell("React + Vite UI — card editor, preview pane, deck manager", 6240, true) ] }),
          new TableRow({ children: [ dataCell("scripts/", 3120, false, true), dataCell("Standalone batch scripts: generate_cards.py, generate_icons.py, generate_assets.py", 6240) ] }),
          new TableRow({ children: [ dataCell("card-data/", 3120, true, true), dataCell("JSON definitions for all cards, decks, layout specs, and icon prompts", 6240, true) ] }),
          new TableRow({ children: [ dataCell("assets/", 3120, false, true), dataCell("Pre-generated borders, icon PNGs, and background images", 6240) ] }),
          new TableRow({ children: [ dataCell("output/", 3120, true, true), dataCell("Generated images: raw-art/, print-ready/ (300 DPI), previews/ (JPEG)", 6240, true) ] }),
          new TableRow({ children: [ dataCell("config.py", 3120, false, true), dataCell("Central model configuration — single place to swap AI model or supporting files", 6240) ] }),
        ],
      }),
      ...spacer(1),

      // ── 3. How a card is stored ────────────────────────────────────────
      heading1("3. How a Card Is Stored"),
      para(
        "Cards live in a SQLite database (managed by the FastAPI backend). Each card record contains all the data " +
        "needed to reconstruct and re-render it at any time."
      ),
      ...spacer(1),

      kvTable([
        ["id", "Unique slug (e.g. sjunk-asteroid-01) — also used as the image filename prefix and deterministic art seed"],
        ["title", "Card name displayed in the title bar"],
        ["deck_id", "Which deck this card belongs to"],
        ["background_id", "Which border/background theme to apply"],
        ["benefits / costs", "JSON objects mapping icon names to counts (e.g. {\"navigation\": 2, \"fame\": 1})"],
        ["description", "Flavour/rules text shown in the info panel"],
        ["art_prompt", "The text prompt sent to the AI model to generate the card art"],
        ["title_size / desc_size", "Font scale override: small, medium, or large"],
        ["show_plus / show_minus", "Whether to render the green + and red - circles on the card edge"],
        ["art_image_path", "Path to the raw AI-generated art PNG (saved for recompositing)"],
        ["print_image_path", "Path to the final 825×1125 px 300 DPI composite PNG"],
        ["preview_image_path", "Path to the 413×563 px JPEG for the UI preview"],
      ]),
      ...spacer(1),

      // ── 4. The AI Model ───────────────────────────────────────────────
      heading1("4. The AI Model — FLUX.1-schnell"),
      para(
        "The app uses FLUX.1-schnell, an open-source text-to-image diffusion model developed by Black Forest Labs. " +
        "It takes a text description and produces a realistic or stylised image from scratch. " +
        "It is not a language model — it does not understand or generate text. Its sole job is image generation."
      ),
      ...spacer(1),

      heading2("4.1 Model Specifications"),

      kvTable([
        ["Model file", "flux1-schnell-Q8_0.gguf"],
        ["Format", "GGUF — a quantised weight format that reduces the model from ~24 GB (full precision) to ~12 GB while preserving most quality"],
        ["Quantisation", "Q8_0 — 8-bit integer quantisation (near full precision; minimal quality loss)"],
        ["Architecture", "Diffusion Transformer (DiT) — the same family as Stable Diffusion 3 and DALL-E 3"],
        ["Inference steps", "4 steps (extremely fast; most models require 20–50 steps)"],
        ["Sampler", "Euler with \"simple\" scheduler"],
        ["Location on disk", "~/Git/ComfyUI/models/unet/flux1-schnell-Q8_0.gguf"],
        ["Model name in code", "Defined once in config.py — FLUX_MODEL_NAME"],
      ]),
      ...spacer(1),

      heading2("4.2 Supporting Models"),
      para("FLUX requires three additional model files loaded alongside the main model:"),
      ...spacer(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2880, 2160, 4320],
        rows: [
          new TableRow({ children: [ headerCell("File", 2880), headerCell("Location", 2160), headerCell("Purpose", 4320) ] }),
          new TableRow({ children: [ dataCell("clip_l.safetensors", 2880, true, true), dataCell("models/clip/", 2160, true), dataCell("CLIP-L text encoder — converts your prompt into a compact embedding the model can read", 4320, true) ] }),
          new TableRow({ children: [ dataCell("t5xxl_fp16.safetensors", 2880, false, true), dataCell("models/clip/", 2160), dataCell("T5-XXL text encoder — a second, larger encoder that gives FLUX much richer language understanding than most image models", 4320) ] }),
          new TableRow({ children: [ dataCell("ae.safetensors", 2880, true, true), dataCell("models/vae/", 2160, true), dataCell("Variational Autoencoder — decodes the model's compressed latent representation into a final pixel image", 4320, true) ] }),
        ],
      }),
      ...spacer(1),

      heading2("4.3 How FLUX Creates an Image"),
      para(
        "FLUX is a diffusion model. Rather than drawing an image directly from a prompt, it starts with random noise " +
        "and gradually refines it into something meaningful over several steps. Here is what happens inside the model " +
        "each time a card is generated:"
      ),
      ...spacer(1),

      pipelineTable([
        {
          num: "1",
          title: "Text encoding",
          desc: "Your art prompt (e.g. \"a rusty asteroid tumbling through space, dramatic lighting, cartoon style\") is fed into two text encoders simultaneously — CLIP-L and T5-XXL. Each encodes the prompt as a numerical vector (an embedding). FLUX uses both encoders together, which gives it much stronger language understanding than models that use only one.",
        },
        {
          num: "2",
          title: "Latent initialisation",
          desc: "The model creates a blank canvas in latent space — a compressed mathematical representation of an image (much smaller than the final pixel grid). This canvas starts as pure random noise. The noise seed is derived from the card ID, so the same card always generates identical art.",
        },
        {
          num: "3",
          title: "Denoising (4 steps)",
          desc: "The Transformer runs 4 denoising steps. In each step it predicts what noise to remove from the current latent, guided by the text embeddings. After 4 steps the latent has been shaped into something that represents the prompt. FLUX achieves this in just 4 steps because it was trained with a flow-matching objective that allows larger, more confident jumps toward the target image.",
        },
        {
          num: "4",
          title: "VAE decode",
          desc: "The finished latent is passed to the Variational Autoencoder (ae.safetensors), which decodes it from the compressed latent space back into full RGB pixels. This is the step that produces the actual image file.",
        },
        {
          num: "5",
          title: "Image returned",
          desc: "ComfyUI saves the decoded PNG to its output folder and makes it available via its /view endpoint. The Cardmaker backend downloads it, saves it as raw art, then hands it to the compositor.",
        },
      ]),
      ...spacer(1),

      calloutBox(
        "Why only 4 steps?",
        "Most diffusion models need 20–50 denoising steps to converge on a quality image. FLUX.1-schnell was trained with " +
        "a \"flow matching\" technique that learns a straighter path from noise to image, reaching acceptable quality in just 4 steps. " +
        "This makes it fast enough to generate card art in seconds on the M4's GPU rather than minutes."
      ),
      ...spacer(1),

      // ── 5. ComfyUI ────────────────────────────────────────────────────
      heading1("5. ComfyUI — The Image Engine"),
      para(
        "ComfyUI is an open-source node-based UI and API server for running image generation models. " +
        "Cardmaker does not use the ComfyUI visual interface — it talks to ComfyUI purely through its HTTP API " +
        "by submitting JSON workflow payloads (called \"prompts\") and polling for results."
      ),
      ...spacer(1),

      heading2("5.1 The Workflow Payload"),
      para(
        "Each generation request is a JSON object describing a graph of nodes. " +
        "The backend builds this programmatically in comfyui.py. The key nodes are:"
      ),
      ...spacer(1),

      kvTable([
        ["UnetLoaderGGUF", "Loads flux1-schnell-Q8_0.gguf from ComfyUI's models/unet/ folder"],
        ["DualCLIPLoader", "Loads clip_l.safetensors and t5xxl_fp16.safetensors"],
        ["VAELoader", "Loads ae.safetensors"],
        ["CLIPTextEncode (x2)", "Encodes the positive prompt and the negative prompt separately"],
        ["EmptyLatentImage", "Creates the blank noise canvas at the target dimensions"],
        ["KSampler", "Runs the 4-step denoising loop (euler sampler, simple scheduler, CFG 1.0)"],
        ["VAEDecode", "Decodes the finished latent to pixels"],
        ["SaveImage", "Writes the PNG to ComfyUI's output directory"],
      ]),
      ...spacer(1),

      heading2("5.2 Negative Prompt"),
      para(
        "A negative prompt tells the model what to avoid. For card art the negative prompt is:"
      ),
      ...spacer(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [9360],
        rows: [
          new TableRow({
            children: [
              codeCell("text, watermark, logo, blurry, low quality, border, frame", 9360),
            ],
          }),
        ],
      }),
      ...spacer(1),

      para(
        "Icon and asset generation use a slightly different negative prompt that also excludes " +
        "\"words, letters, multiple objects, busy background\" to keep icons clean and isolated."
      ),
      ...spacer(1),

      // ── 6. Card generation pipeline ───────────────────────────────────
      heading1("6. Card Generation Pipeline"),
      para(
        "When you click Generate on a card in the UI, the following sequence runs end to end."
      ),
      ...spacer(1),

      pipelineTable([
        {
          num: "1",
          title: "UI trigger",
          desc: "The React frontend sends POST /api/cards/{card_id}/generate to the FastAPI backend.",
        },
        {
          num: "2",
          title: "ComfyUI check",
          desc: "The backend pings GET /system_stats on ComfyUI (port 8188). If ComfyUI is not running, it returns HTTP 503 immediately.",
        },
        {
          num: "3",
          title: "Seed derivation",
          desc: "A deterministic seed is derived from the card ID using Python's hash() function modulo 2^32. The same card always gets the same seed and therefore the same art image, unless you change the art prompt.",
        },
        {
          num: "4",
          title: "Prompt submission",
          desc: "The backend builds the ComfyUI workflow JSON and posts it to POST /prompt. ComfyUI queues the job and returns a prompt_id.",
        },
        {
          num: "5",
          title: "Polling",
          desc: "The backend polls GET /history/{prompt_id} every 2 seconds until ComfyUI reports the job is finished (timeout: 5 minutes).",
        },
        {
          num: "6",
          title: "Image download",
          desc: "The backend fetches the generated PNG from GET /view and holds it in memory as a PIL Image object.",
        },
        {
          num: "7",
          title: "Raw art saved",
          desc: "The raw AI art is saved to output/raw-art/{card_id}_art.png at 300 DPI. This lets you recomposite the card later (e.g. after tweaking text or icons) without re-running the model.",
        },
        {
          num: "8",
          title: "Compositing",
          desc: "compositor.composite_card() layers the art behind the title bar and info panel, draws the description text, and places the icon rows. Then apply_border() composites the themed border overlay. Finally draw_pm_overlay() draws the green + and red - circles on the card edge.",
        },
        {
          num: "9",
          title: "Output saved",
          desc: "Two files are written: a 825×1125 px 300 DPI PNG to output/print-ready/ (ready for the print house), and a 413×563 px JPEG to output/previews/ for the UI.",
        },
        {
          num: "10",
          title: "DB updated",
          desc: "The card record in SQLite is updated with the new file paths. The API returns the updated card record to the frontend, which refreshes the preview pane.",
        },
      ]),
      ...spacer(1),

      // ── 7. Card compositing ───────────────────────────────────────────
      heading1("7. Card Compositing"),
      para(
        "The compositor (compositor.py) builds the final card image in layers using the Pillow image library. " +
        "No template files are involved — every zone is drawn programmatically from the card data and layout JSON."
      ),
      ...spacer(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2160, 7200],
        rows: [
          new TableRow({ children: [ headerCell("Layer (bottom to top)", 2160), headerCell("What is drawn", 7200) ] }),
          new TableRow({ children: [ dataCell("Background", 2160, true, true), dataCell("Dark canvas (RGB 30, 30, 40) at 825×1125 px — the card base", 7200, true) ] }),
          new TableRow({ children: [ dataCell("Header bar", 2160, false, true), dataCell("White rounded rectangle containing the card title and benefit icons row, sized dynamically to the content", 7200) ] }),
          new TableRow({ children: [ dataCell("Card art", 2160, true, true), dataCell("AI-generated image cropped and resized to fill all space between the header and info panel", 7200, true) ] }),
          new TableRow({ children: [ dataCell("Info panel", 2160, false, true), dataCell("White rounded rectangle at the bottom containing the description text and cost icons row", 7200) ] }),
          new TableRow({ children: [ dataCell("Border overlay", 2160, true, true), dataCell("Pre-generated themed border PNG (with centre cut out) composited on top, giving each deck a distinct look", 7200, true) ] }),
          new TableRow({ children: [ dataCell("+ / - circles", 2160, false, true), dataCell("Green + and red - circles drawn last, straddling the left card edge to indicate gain/spend actions", 7200) ] }),
        ],
      }),
      ...spacer(1),

      // ── 8. Batch scripts ──────────────────────────────────────────────
      heading1("8. Batch Scripts"),
      para(
        "Three standalone Python scripts handle bulk generation outside the web UI. " +
        "They all read model settings from config.py and call ComfyUI directly."
      ),
      ...spacer(1),

      kvTable([
        ["scripts/generate_cards.py", "Iterates over all cards in card-data/space_junk_cards.json, generates art for each via ComfyUI, and composites print-ready card images to output/print-ready/"],
        ["scripts/generate_icons.py", "Generates the game icon PNGs (compass, oscar, gold bar, etc.) using short prompts defined in assets/icons/prompts.json. Icons are cropped to square and saved to assets/icons/"],
        ["scripts/generate_assets.py", "Generates deck back images and card border overlays. Each border is generated as a full-image texture, then the compositor cuts out the centre at runtime to create the frame effect"],
      ]),
      ...spacer(1),

      // ── 9. Running the app ────────────────────────────────────────────
      heading1("9. Running the App"),

      heading2("Starting ComfyUI"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [9360],
        rows: [
          new TableRow({ children: [ codeCell("cd ~/Git/ComfyUI && python main.py", 9360) ] }),
        ],
      }),
      ...spacer(1),

      heading2("Starting the backend"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [9360],
        rows: [
          new TableRow({ children: [ codeCell("cd ~/Git/Cardmaker-App/app/backend && uvicorn main:app --reload", 9360) ] }),
        ],
      }),
      ...spacer(1),

      heading2("Starting the frontend"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [9360],
        rows: [
          new TableRow({ children: [ codeCell("cd ~/Git/Cardmaker-App/app/frontend && npm run dev", 9360) ] }),
        ],
      }),
      ...spacer(1),

      para("The frontend runs at http://localhost:5173. The backend API is at http://localhost:8000. ComfyUI runs at http://localhost:8188.", { italic: true }),
      ...spacer(1),

      heading2("Changing the model"),
      para(
        "All four places that reference the model (comfyui.py and the three batch scripts) import from a single file. " +
        "To switch models, edit one line in config.py:"
      ),
      ...spacer(1),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [9360],
        rows: [
          new TableRow({ children: [ codeCell("FLUX_MODEL_NAME = \"flux1-schnell-Q8_0.gguf\"   # change this", 9360) ] }),
        ],
      }),
      ...spacer(1),

      // ── 10. Card specs ─────────────────────────────────────────────────
      heading1("10. Card Specifications"),

      kvTable([
        ["Physical size", "2.5\" × 3.5\" (standard poker size)"],
        ["With bleed", "2.75\" × 3.75\""],
        ["Pixel dimensions", "825 × 1125 px"],
        ["Resolution", "300 DPI (print-ready)"],
        ["Colour space", "RGB (PNG for print, JPEG for preview)"],
        ["Preview size", "413 × 563 px JPEG at 85% quality"],
        ["Art seed", "Deterministic — derived from card ID so re-generation produces identical art"],
      ]),

    ], // end children
  }], // end sections
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("cardmaker_overview.docx", buffer);
  console.log("Done: cardmaker_overview.docx");
});
