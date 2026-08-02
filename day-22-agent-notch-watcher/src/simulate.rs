use reqwest::Client;
use serde_json::json;
use std::time::Duration;
use tokio::time::sleep;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🚀 Launching Agent Notch Watcher Demo Simulation Sequence...");
    let client = Client::new();
    let url = "http://127.0.0.1:8765/event";

    // Step 1: Idle with Claude Starburst Logo
    println!("Step 1: Claude Idle (Ready)");
    client
        .post(url)
        .json(&json!({
            "agent_type": "anthropic",
            "status": "idle",
            "step_description": "Claude 3.5 Sonnet • Ready",
            "tokens_used": 74200,
            "glow_setting": "max"
        }))
        .send()
        .await?;
    sleep(Duration::from_secs(3)).await;

    // Step 2: Claude Thinking
    println!("Step 2: Claude Thinking (Animated Pulsing Aura)");
    client
        .post(url)
        .json(&json!({
            "agent_type": "anthropic",
            "status": "thinking",
            "step_description": "Evaluating multi-step legal retrieval context...",
            "tokens_used": 76500,
            "glow_setting": "max"
        }))
        .send()
        .await?;
    sleep(Duration::from_secs(3)).await;

    // Step 3: Tool Execution (grep_search)
    println!("Step 3: Tool Execution (grep_search)");
    client
        .post(url)
        .json(&json!({
            "agent_type": "anthropic",
            "status": "toolexecuting",
            "step_description": "Executing tool: grep_search(\"AGENTS.md\")",
            "tokens_used": 78900,
            "glow_setting": "max"
        }))
        .send()
        .await?;
    sleep(Duration::from_secs(3)).await;

    // Step 4: Switch to Gemini Brand Logo
    println!("Step 4: Switch to Google Gemini");
    client
        .post(url)
        .json(&json!({
            "agent_type": "gemini",
            "status": "thinking",
            "step_description": "Gemini 1.5 Pro • Synthesizing contract clauses",
            "tokens_used": 83400,
            "glow_setting": "subtle"
        }))
        .send()
        .await?;
    sleep(Duration::from_secs(3)).await;

    // Step 5: Switch to OpenAI / ChatGPT
    println!("Step 5: Switch to OpenAI GPT-4o");
    client
        .post(url)
        .json(&json!({
            "agent_type": "openai",
            "status": "toolexecuting",
            "step_description": "GPT-4o • Calling code interpreter",
            "tokens_used": 89200,
            "glow_setting": "subtle"
        }))
        .send()
        .await?;
    sleep(Duration::from_secs(3)).await;

    // Step 6: Session Quota Warning Threshold (94% used)
    println!("Step 6: Quota Warning Threshold (94% used)");
    client
        .post(url)
        .json(&json!({
            "agent_type": "openai",
            "status": "quotawarning",
            "step_description": "CRITICAL: Approaching 100k token session limit!",
            "tokens_used": 94100,
            "glow_setting": "max"
        }))
        .send()
        .await?;
    sleep(Duration::from_secs(3)).await;

    // Step 6b: Permission Request Simulation
    println!("Step 6b: Triggering Blocking Permission Request");
    let perm_client = client.clone();
    tokio::spawn(async move {
        let perm_url = "http://127.0.0.1:8765/permission/request";
        let res = perm_client
            .post(perm_url)
            .json(&json!({
                "request_id": "perm-sim-001",
                "session_id": "claude-sim",
                "agent_name": "Claude Code",
                "action_type": "file_edit",
                "details": "replace_file_content target=\"src/main.rs\"",
                "timeout_seconds": 10
            }))
            .send()
            .await;
        if let Ok(resp) = res {
            println!("Received Permission Response: {:?}", resp.text().await.unwrap_or_default());
        }
    });
    sleep(Duration::from_secs(3)).await;

    // Step 6c: Launch Session Simulation
    println!("Step 6c: Launching New Agent Session via HUD API");
    let launch_url = "http://127.0.0.1:8765/session/launch";
    let launch_res = client
        .post(launch_url)
        .json(&json!({
            "agent_command": "ollama",
            "working_directory": "/Users/tjlsmith0831/Desktop/Programming/50-days-of-dev",
            "initial_prompt": "run llama3"
        }))
        .send()
        .await;
    if let Ok(resp) = launch_res {
        println!("Launch Response: {:?}", resp.text().await.unwrap_or_default());
    }
    sleep(Duration::from_secs(3)).await;

    // Step 7: Return to Claude Idle
    println!("Step 7: Resetting to Claude Ready");
    client
        .post(url)
        .json(&json!({
            "agent_type": "anthropic",
            "status": "idle",
            "step_description": "Claude 3.5 Sonnet • Ready",
            "tokens_used": 74200,
            "glow_setting": "max"
        }))
        .send()
        .await?;


    println!("✅ Simulation sequence completed successfully!");
    Ok(())
}
