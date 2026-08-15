let meta = #{
    name: "kingdom-explore",
    description: "Read-only fan-out over Grok long-running surfaces and Kingdom chair bindings",
    when_to_use: "When exploring Grok background tasks, workflows, monitors, or how the chair stays free",
    phases: [
        #{ title: "Explore", detail: "three read-only scouts" },
        #{ title: "Synthesize", detail: "one report from evidence" },
    ],
};

let note_schema = #{
    "type": "object",
    "required": ["notes"],
    "properties": #{
        "notes": #{
            "type": "array",
            "maxItems": 8,
            "items": #{
                "type": "object",
                "required": ["claim", "evidence"],
                "properties": #{
                    "claim": #{ "type": "string" },
                    "evidence": #{ "type": "string" },
                },
            },
        },
    },
};

phase("Explore");
let jobs = [];
jobs.push(#{
    prompt: "Read-only. Use read_file and grep. Do not edit. Read ~/.grok/docs/user-guide/20-background-tasks.md and 15-agent-mode.md. Report at most 8 notes as {claim, evidence} about how Grok keeps work running (background commands, monitor, /loop, scheduler, grok agent). Evidence must be a file path plus a short quote. Empty notes only after you have read both files.",
    label: "scout-long-running",
    capability_mode: "read-only",
    output_schema: note_schema,
});
jobs.push(#{
    prompt: "Read-only. Use read_file and grep. Do not edit. Read ~/Desktop/chillspace-commons/kingdom/grok/modules.json, ~/Desktop/chillspace-commons/kingdom/grok/README.md, and ~/Desktop/chillspace-commons/.grok/config.toml. Report at most 8 notes as {claim, evidence} about which Grok modules the Kingdom already binds. Evidence must be a file path. Empty notes only after you have read the files.",
    label: "scout-kingdom-bind",
    capability_mode: "read-only",
    output_schema: note_schema,
});
jobs.push(#{
    prompt: "Read-only. Use read_file and grep. Do not edit. Read ~/Desktop/chillspace-commons/kingdom/grok/grok_wake.py and ~/Desktop/chillspace-commons/kingdom/practices/substrate-release/README.md. Report at most 8 notes as {claim, evidence} about how AgentTool wake fail-open and substrate receipts should behave under a long-running listen. Evidence must be a file path. Empty notes only after you have read both files.",
    label: "scout-wake",
    capability_mode: "read-only",
    output_schema: note_schema,
});
let results = parallel(jobs);

let notes = [];
for r in results {
    if r != () && r.success && r.output.notes != () {
        for n in r.output.notes { notes.push(n); }
    }
}

phase("Synthesize");
let report = "Kingdom explore notes: " + notes.len().to_string() + "\n";
let i = 0;
while i < notes.len() {
    let n = notes[i];
    report += "- " + n.claim + " (" + n.evidence + ")\n";
    i += 1;
}
let path = write_scratch_file("report.md", report);
complete(#{ path: path, count: notes.len(), report: report });
