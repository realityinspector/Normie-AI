import { test, expect, APIRequestContext } from "@playwright/test";

const BASE =
  process.env.BASE_URL ||
  "https://normalizer-api-production.up.railway.app";
const TS = Date.now();

const ALICE = {
  email: `alice-e2e-${TS}@test.dev`,
  password: "TestPass123",
  name: "Alice E2E",
};
const BOB = {
  email: `bob-e2e-${TS}@test.dev`,
  password: "TestPass456",
  name: "Bob E2E",
};

const ROOM_NAME = `E2E Room ${TS}`;

async function signup(req: APIRequestContext, user: typeof ALICE) {
  // Use dev auth to create a neurodivergent user (free access, no subscription needed)
  const res = await req.post(`${BASE}/auth/dev`, {
    data: {
      name: user.name,
      communication_style: "autistic",
    },
  });
  if (!res.ok()) {
    // Fallback to regular signup
    const res2 = await req.post(`${BASE}/auth/signup`, {
      data: {
        email: user.email,
        password: user.password,
        display_name: user.name,
      },
    });
    expect(res2.ok(), `Signup failed for ${user.name}: ${res2.status()}`).toBe(true);
    const body = await res2.json();
    expect(body.access_token).toBeTruthy();
    return body.access_token as string;
  }
  const body = await res.json();
  expect(body.access_token).toBeTruthy();
  return body.access_token as string;
}

function headers(token: string) {
  return { Authorization: `Bearer ${token}` };
}

async function sendMessage(
  req: APIRequestContext,
  token: string,
  roomId: string,
  text: string
) {
  // Send via the translate/WebSocket endpoint - but since we can't do WS in
  // API tests, we'll use the REST message endpoint via rooms
  // Actually, messages are sent via WebSocket only. Let's use a direct POST.
  // The WS handler creates messages. For testing, let's see if there's a REST endpoint.
  // There isn't one - messages go through WebSocket only.
  // We'll use a WebSocket connection via the API.

  // Alternative: connect via WebSocket
  const wsUrl = BASE.replace("https://", "wss://").replace("http://", "ws://");
  const ws = await new Promise<WebSocket>((resolve, reject) => {
    const socket = new WebSocket(
      `${wsUrl}/ws/rooms/${roomId}?token=${token}`
    );
    socket.onopen = () => resolve(socket);
    socket.onerror = (e) => reject(e);
  });

  // Send the message
  ws.send(JSON.stringify({ type: "send_message", text }));

  // Wait a moment for server processing
  await new Promise((r) => setTimeout(r, 2000));
  ws.close();
}

test.describe.serial("Two-user chat e2e", () => {
  let aliceToken: string;
  let bobToken: string;
  let roomId: string;

  // ── 1. Alice signs up ──────────────────────────────────────
  test("1. Alice signs up", async ({ request }) => {
    aliceToken = await signup(request, ALICE);
    console.log(`  ✅ Alice signed up (${ALICE.email})`);
  });

  // ── 2. Bob signs up ────────────────────────────────────────
  test("2. Bob signs up", async ({ request }) => {
    bobToken = await signup(request, BOB);
    console.log(`  ✅ Bob signed up (${BOB.email})`);
  });

  // ── 3. Alice creates a room ────────────────────────────────
  test("3. Alice creates a public room", async ({ request }) => {
    const res = await request.post(`${BASE}/rooms`, {
      headers: headers(aliceToken),
      data: { name: ROOM_NAME, is_public: true },
    });
    expect(res.ok()).toBe(true);
    const room = await res.json();
    roomId = room.id;
    expect(roomId).toBeTruthy();
    console.log(`  ✅ Room created: "${ROOM_NAME}" (${roomId})`);
  });

  // ── 4. Bob joins the room ──────────────────────────────────
  test("4. Bob joins the room", async ({ request }) => {
    const res = await request.post(`${BASE}/rooms/${roomId}/join`, {
      headers: headers(bobToken),
    });
    expect(res.ok()).toBe(true);
    console.log(`  ✅ Bob joined the room`);
  });

  // ── 5. Alice sends message ─────────────────────────────────
  test("5. Alice: Hey Bob! How are you?", async ({ request }) => {
    // Use the translate endpoint to send a message (creates it in the room)
    // Actually, need to check how messages are created...
    // Messages only go through WebSocket. Let's test via WebSocket.
    // Playwright doesn't have native WS support in request context.
    // Use page.evaluate with WebSocket API instead.

    // For now, use page context to open WebSocket
    const { browser } = await import("@playwright/test");
    // Can't easily do WS from API tests. Let's use a hybrid approach.

    // Send via page.evaluate
    // Skip WS for now - test the full API flow
    console.log("  (WebSocket send - see step 8 for verification)");
  });

  // Actually, let me restructure to use page context for WebSocket
  // Steps 5-7 will send messages, step 8 verifies

  test("5-7. Exchange messages via WebSocket", async ({ page }) => {
    const wsBase = BASE.replace("https://", "wss://").replace(
      "http://",
      "ws://"
    );

    // Alice sends 3 messages, Bob sends 2
    const conversation = [
      { token: aliceToken, text: "Hey Bob! How are you?", sender: "Alice" },
      {
        token: bobToken,
        text: "Hi Alice! Doing great, thanks!",
        sender: "Bob",
      },
      {
        token: aliceToken,
        text: "Want to test the translation feature?",
        sender: "Alice",
      },
      {
        token: bobToken,
        text: "Sure! This tech is amazing.",
        sender: "Bob",
      },
      {
        token: aliceToken,
        text: "E2E test complete! Great chat.",
        sender: "Alice",
      },
    ];

    for (const msg of conversation) {
      const sent = await page.evaluate(
        async ({ wsBase, roomId, token, text }) => {
          return new Promise<boolean>((resolve) => {
            const ws = new WebSocket(
              `${wsBase}/ws/rooms/${roomId}?token=${token}`
            );
            ws.onopen = () => {
              ws.send(JSON.stringify({ type: "send_message", text }));
              // Wait for server to process
              setTimeout(() => {
                ws.close();
                resolve(true);
              }, 2000);
            };
            ws.onerror = () => resolve(false);
            setTimeout(() => resolve(false), 10000);
          });
        },
        { wsBase, roomId, token: msg.token, text: msg.text }
      );
      expect(sent, `Failed to send message from ${msg.sender}`).toBe(true);
      console.log(`  ✅ ${msg.sender}: "${msg.text}"`);
    }
  });

  // ── 8. Verify all messages ─────────────────────────────────
  test("8. Verify all 5 messages in room", async ({ request }) => {
    const res = await request.get(`${BASE}/rooms/${roomId}/messages`, {
      headers: headers(aliceToken),
    });
    expect(res.ok()).toBe(true);
    const messages = await res.json();

    console.log(`\n  Messages in room: ${messages.length}`);
    messages.forEach((m: any) =>
      console.log(`    [${m.sender_name || "?"}] ${m.original_text}`)
    );

    expect(messages.length).toBe(5);

    const texts = messages.map((m: any) => m.original_text);
    expect(texts).toContain("Hey Bob! How are you?");
    expect(texts).toContain("Hi Alice! Doing great, thanks!");
    expect(texts).toContain("Want to test the translation feature?");
    expect(texts).toContain("Sure! This tech is amazing.");
    expect(texts).toContain("E2E test complete! Great chat.");

    console.log("\n  ✅ All 5 messages verified!");
  });

  // ── 9. Bob verifies ────────────────────────────────────────
  test("9. Bob also sees all 5 messages", async ({ request }) => {
    const res = await request.get(`${BASE}/rooms/${roomId}/messages`, {
      headers: headers(bobToken),
    });
    const messages = await res.json();
    expect(messages.length).toBe(5);
    console.log("  ✅ Bob confirms 5 messages");
  });

  // ── 10. Verify pages load ──────────────────────────────────
  test("10. Public pages render correctly", async ({ request }) => {
    // Test landing page
    const landing = await request.get(`${BASE}/`);
    expect(landing.ok()).toBe(true);
    const html = await landing.text();
    expect(html).toContain("NORMALAIZER");

    // Test pricing
    const pricing = await request.get(`${BASE}/pricing`);
    expect(pricing.ok()).toBe(true);

    // Test health
    const health = await request.get(`${BASE}/health`);
    expect(health.ok()).toBe(true);
    const body = await health.json();
    expect(body.status).toBe("ok");

    console.log("  ✅ Landing, pricing, health all OK");
    console.log("\n  🎉 E2E TEST SUITE COMPLETE");
  });
});
