import "dotenv/config";
import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
import * as readline from "readline";
import { readFileSync } from "fs";
import { join } from "path";
import { homedir } from "os";

const COLORS = {
  reset: "\x1b[0m",
  dim: "\x1b[2m",
  italic: "\x1b[3m",
  cyan: "\x1b[36m",
  yellow: "\x1b[33m",
  green: "\x1b[32m",
  magenta: "\x1b[35m",
  bold: "\x1b[1m",
};

const MODELS = [
  { name: "claude-sonnet-4-20250514", provider: "anthropic" as const },
  { name: "gpt-4o", provider: "openai" as const },
  { name: "gpt-4o-mini", provider: "openai" as const },
  { name: "gpt-4.1", provider: "openai" as const },
  { name: "gpt-4.1-mini", provider: "openai" as const },
  { name: "o3-mini", provider: "openai" as const },
];

function ask(question: string): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer);
    });
  });
}

function loadOpenAIKey(): string {
  const keyPath = join(homedir(), "OneDrive - Microsoft", "Desktop", "openai_key.txt");
  try {
    return readFileSync(keyPath, "utf-8").trim();
  } catch {
    console.error(`${COLORS.yellow}Error: Could not read OpenAI key from ${keyPath}${COLORS.reset}`);
    process.exit(1);
  }
}

async function runAnthropic(prompt: string) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey || apiKey === "sk-ant-your-key-here") {
    console.error(`${COLORS.yellow}Error: Set your ANTHROPIC_API_KEY in the .env file${COLORS.reset}`);
    process.exit(1);
  }

  const client = new Anthropic({ apiKey });

  console.log(`${COLORS.dim}Thinking: enabled | Interleaved: on${COLORS.reset}\n`);

  let thinkingRound = 0;

  const response = await client.messages.create(
    {
      model: "claude-sonnet-4-20250514",
      max_tokens: 16000,
      thinking: { type: "enabled", budget_tokens: 10000 },
      messages: [{ role: "user", content: prompt }],
      stream: true,
    },
    { headers: { "anthropic-beta": "interleaved-thinking-2025-05-14" } },
  );

  for await (const event of response) {
    if (event.type === "content_block_start") {
      if (event.content_block.type === "thinking") {
        thinkingRound++;
        const label = thinkingRound > 1 ? `∴ Thinking again (round ${thinkingRound})...` : `∴ Thinking...`;
        process.stdout.write(`${COLORS.dim}${COLORS.italic}${COLORS.magenta}${label}\n\n`);
      } else if (event.content_block.type === "text") {
        process.stdout.write(`${COLORS.reset}\n\n${COLORS.dim}─────────────────────────────────${COLORS.reset}\n\n`);
        process.stdout.write(`${COLORS.bold}${COLORS.green}Response:${COLORS.reset}\n\n`);
      }
    } else if (event.type === "content_block_delta") {
      if (event.delta.type === "thinking_delta") {
        process.stdout.write(`${COLORS.dim}${COLORS.italic}${event.delta.thinking}${COLORS.reset}`);
      } else if (event.delta.type === "text_delta") {
        process.stdout.write(event.delta.text);
      }
    } else if (event.type === "message_delta") {
      console.log(`\n\n${COLORS.dim}─────────────────────────────────${COLORS.reset}`);
      console.log(`${COLORS.cyan}Usage:${COLORS.reset}`);
      console.log(`  Output tokens:   ${event.usage.output_tokens}`);
    }
  }
}

async function runOpenAI(model: string, prompt: string) {
  const apiKey = loadOpenAIKey();
  const client = new OpenAI({ apiKey });

  const stream = await client.chat.completions.create({
    model,
    messages: [{ role: "user", content: prompt }],
    stream: true,
  });

  process.stdout.write(`${COLORS.bold}${COLORS.green}Response:${COLORS.reset}\n\n`);

  for await (const chunk of stream) {
    const text = chunk.choices[0]?.delta?.content;
    if (text) process.stdout.write(text);
  }

  console.log(`\n\n${COLORS.dim}─────────────────────────────────${COLORS.reset}`);
}

async function main() {
  console.log(`\n${COLORS.bold}${COLORS.cyan}AI Chat POC${COLORS.reset}\n`);
  console.log(`${COLORS.cyan}Choose a model:${COLORS.reset}`);
  MODELS.forEach((m, i) => {
    console.log(`  ${COLORS.bold}${i + 1}${COLORS.reset}) ${m.name} ${COLORS.dim}(${m.provider})${COLORS.reset}`);
  });
  console.log();

  const choice = await ask(`${COLORS.green}Select model (1-${MODELS.length}): ${COLORS.reset}`);
  const idx = parseInt(choice, 10) - 1;
  if (isNaN(idx) || idx < 0 || idx >= MODELS.length) {
    console.log("Invalid selection. Exiting.");
    process.exit(1);
  }

  const selected = MODELS[idx];
  console.log(`\n${COLORS.dim}Model: ${selected.name}${COLORS.reset}\n`);

  const prompt = await ask(`${COLORS.green}Your prompt: ${COLORS.reset}`);
  if (!prompt.trim()) {
    console.log("No prompt provided. Exiting.");
    process.exit(0);
  }

  console.log();

  if (selected.provider === "anthropic") {
    await runAnthropic(prompt);
  } else {
    await runOpenAI(selected.name, prompt);
  }
}

main().catch((err) => {
  console.error(`\n${COLORS.yellow}Error: ${err.message}${COLORS.reset}`);
  process.exit(1);
});
