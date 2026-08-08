import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, classifyQueryResult, connectDemo, disconnectDemo, getSchema, runQuery } from "./api/client.js";
import { useTheme } from "./hooks/useTheme.js";
import { parseSchema } from "./lib/parseSchema.js";
import { generateSampleQuestions } from "./lib/sampleQuestions.js";
import NavBar from "./components/NavBar.jsx";
import Hero from "./components/Hero.jsx";
import QueryConsole from "./components/QueryConsole.jsx";
import ResultPanel from "./components/ResultPanel.jsx";
import HowItWorks from "./components/HowItWorks.jsx";
import SchemaPanel from "./components/SchemaPanel.jsx";
import DemoConnect from "./components/DemoConnect.jsx";
import LLMKeyPanel from "./components/LLMKeyPanel.jsx";
import Footer from "./components/Footer.jsx";
import styles from "./App.module.css";

const PROVIDER_LABELS = { groq: "Groq", openai: "OpenAI" };

export default function App() {
  const { theme, toggle: toggleTheme } = useTheme();

  const [demoSession, setDemoSession] = useState(null); // { sessionId, expiresInSeconds } | null
  const [isConnecting, setIsConnecting] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [connectError, setConnectError] = useState(null);

  const [llmOverride, setLlmOverride] = useState(null); // { provider, apiKey, model } | null — never persisted

  const [schemaContext, setSchemaContext] = useState("");
  const [schemaLoading, setSchemaLoading] = useState(true);
  const [schemaError, setSchemaError] = useState(null);

  const [queryState, setQueryState] = useState(null);
  const stageTimer = useRef(null);

  const loadSchema = useCallback(async (sessionId, { refresh = false } = {}) => {
    setSchemaLoading(true);
    setSchemaError(null);
    try {
      const data = await getSchema({ sessionId, refresh });
      setSchemaContext(data.schema_context);
    } catch (err) {
      setSchemaError(err instanceof ApiError ? err.message : "Couldn't load the schema.");
    } finally {
      setSchemaLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSchema(null);
  }, [loadSchema]);

  useEffect(() => () => clearInterval(stageTimer.current), []);

  async function handleConnect(connectionString) {
    setIsConnecting(true);
    setConnectError(null);
    try {
      const data = await connectDemo(connectionString);
      const session = { sessionId: data.session_id, expiresInSeconds: data.expires_in_seconds };
      setDemoSession(session);
      setQueryState(null);
      await loadSchema(session.sessionId);
    } catch (err) {
      setConnectError(err instanceof ApiError ? err.message : "Couldn't connect.");
    } finally {
      setIsConnecting(false);
    }
  }

  async function handleDisconnect() {
    if (!demoSession) return;
    setIsDisconnecting(true);
    try {
      await disconnectDemo(demoSession.sessionId);
    } catch {
      // Best-effort — the session will expire on its own either way.
    } finally {
      setDemoSession(null);
      setQueryState(null);
      setIsDisconnecting(false);
      loadSchema(null);
    }
  }

  async function handleQuerySubmit(question) {
    clearInterval(stageTimer.current);
    setQueryState({ status: "loading", stage: 0 });
    stageTimer.current = setInterval(() => {
      setQueryState((current) =>
        current?.status === "loading" ? { status: "loading", stage: current.stage + 1 } : current,
      );
    }, 900);

    try {
      const data = await runQuery(question, demoSession?.sessionId, llmOverride);
      const classified = classifyQueryResult(data);
      setQueryState({ status: classified.kind, data: classified });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.kind === "session") {
          setDemoSession(null);
          loadSchema(null);
        }
        // A bad BYOK key is left in place on purpose — the user should see
        // the error and fix it, not have their input silently wiped.
        setQueryState({ status: "error", kind: err.kind, message: err.message });
      } else {
        setQueryState({ status: "error", kind: "unknown", message: "Something went wrong." });
      }
    } finally {
      clearInterval(stageTimer.current);
    }
  }

  const sampleQuestions = useMemo(() => generateSampleQuestions(parseSchema(schemaContext)), [schemaContext]);

  const dbLabel = demoSession ? "your connected database" : "the sample database";
  const llmLabel = llmOverride
    ? `your ${PROVIDER_LABELS[llmOverride.provider] ?? llmOverride.provider} key`
    : "the server's default model";
  const contextLabel = `Querying ${dbLabel} · via ${llmLabel}`;
  const schemaSourceLabel = demoSession ? "Your connected database" : "Sample database (orders, products)";

  return (
    <>
      <NavBar theme={theme} onToggleTheme={toggleTheme} />

      <Hero>
        <QueryConsole
          onSubmit={handleQuerySubmit}
          isLoading={queryState?.status === "loading"}
          contextLabel={contextLabel}
          sampleQuestions={sampleQuestions}
        />
        <ResultPanel state={queryState} />
      </Hero>

      <HowItWorks />

      <section id="workspace" className={styles.workspace}>
        <div className={`${styles.workspaceInner} container`}>
          <div className={styles.schemaArea}>
            <SchemaPanel
              schemaContext={schemaContext}
              isLoading={schemaLoading}
              error={schemaError}
              onRefresh={() => loadSchema(demoSession?.sessionId, { refresh: true })}
              sourceLabel={schemaSourceLabel}
            />
          </div>
          <div className={styles.demoArea}>
            <DemoConnect
              session={demoSession}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              isConnecting={isConnecting}
              isDisconnecting={isDisconnecting}
              error={connectError}
            />
          </div>
          <div className={styles.llmArea}>
            <LLMKeyPanel override={llmOverride} onSave={setLlmOverride} onClear={() => setLlmOverride(null)} />
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
