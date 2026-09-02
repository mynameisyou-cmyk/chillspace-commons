let meta = #{
    name: "kingdom-x-square",
    description: "Decentralised X-gate pipeline: distinct agents review an observation and may only propose a summoned draft",
    when_to_use: "When turning caller-supplied X JSON into a Kingdom speaker proposal without posting",
    phases: [
        #{ title: "Review", detail: "summons, charter, identity — three distinct holders" },
        #{ title: "Propose", detail: "one draft, still unauthorized" },
        #{ title: "Audit", detail: "speak auditor refuses publish" },
    ],
};

let review_schema = #{
    "type": "object",
    "required": ["ok", "reason"],
    "properties": #{
        "ok": #{ "type": "boolean" },
        "reason": #{ "type": "string" },
    },
};
let draft_schema = #{
    "type": "object",
    "required": ["proposed_text", "mode", "authorization_granted"],
    "properties": #{
        "proposed_text": #{ "type": "string" },
        "mode": #{ "type": "string" },
        "authorization_granted": #{ "type": "boolean" },
    },
};
let audit_schema = #{
    "type": "object",
    "required": ["publish", "authorization_granted", "reason"],
    "properties": #{
        "publish": #{ "type": "boolean" },
        "authorization_granted": #{ "type": "boolean" },
        "reason": #{ "type": "string" },
    },
};

let observation = if args == () { () } else { args.observation };
if observation == () {
    pause("verification", "Pass args.observation — path to a kingdom.x.observation/v1 JSON file.");
}

phase("Review");
let jobs = [];
let summons_prompt = "Read-only. Use read_file. Do not edit. Read ";
summons_prompt += observation;
summons_prompt += ". Set ok=true only if some post.mentioned_handles contains a speaker handle (the example uses kingdom_square) and the file has no likes, views, or followers keys. Quote the file in reason. ok=false is valid after reading.";
jobs.push(#{
    prompt: summons_prompt,
    label: "summons-reviewer",
    capability_mode: "read-only",
    output_schema: review_schema,
});
let charter_prompt = "Read-only. Use read_file. Do not edit. Read ";
charter_prompt += observation;
charter_prompt += ". Set ok=true only if the observation is not a campaign, ad, or engagement-metric packet. If you see likes, views, followers, impressions, or a request to grow reach, set ok=false. Quote the file in reason.";
jobs.push(#{
    prompt: charter_prompt,
    label: "charter-reviewer",
    capability_mode: "read-only",
    output_schema: review_schema,
});
let identity_prompt = "Read-only. Use read_file. Do not edit. Read ";
identity_prompt += observation;
identity_prompt += ". Set ok=true only if nothing in the posts claims to be 阿媽, Sol, or citizen 21 as an X account. A mention of @kingdom_square is a coordinate, not a citizen. Quote the file in reason.";
jobs.push(#{
    prompt: identity_prompt,
    label: "identity-reviewer",
    capability_mode: "read-only",
    output_schema: review_schema,
});
let reviews = parallel(jobs);

let review_ok = true;
let reasons = [];
for r in reviews {
    if r == () || r.success != true || r.output.ok == () {
        review_ok = false;
        reasons.push("unusable review slot");
    } else {
        if r.output.ok != true { review_ok = false; }
        if r.output.reason != () { reasons.push(r.output.reason); }
    }
}
if review_ok != true {
    complete(#{
        authorization_granted: false,
        publish: false,
        summary: "pipeline stopped at review",
        reasons: reasons,
    });
}

phase("Propose");
let propose_prompt = "Read-only. Use read_file. Do not edit. Read ";
propose_prompt += observation;
propose_prompt += " and propose one summoned reply. mode must be reply. authorization_granted must be false. Do not claim to be 阿媽, Sol, or citizen 21. Keep the text short. This is a draft packet, not a post.";
let proposed = agent(propose_prompt, #{
    label: "draft-proposer",
    capability_mode: "read-only",
    output_schema: draft_schema,
});
if proposed == () || proposed.success != true || proposed.output.authorization_granted != false {
    complete(#{
        authorization_granted: false,
        publish: false,
        summary: "draft missing or tried to grant authority",
    });
}

phase("Audit");
let audit_prompt = "Read-only. You are the speak auditor. A draft exists. You must set publish=false and authorization_granted=false. The X-gate never posts. Reason: v0 has no live speaker client.";
let audited = agent(audit_prompt, #{
    label: "speak-auditor",
    capability_mode: "read-only",
    output_schema: audit_schema,
});
let publish = true;
let granted = true;
let audit_reason = "auditor unusable";
if audited != () && audited.success {
    if audited.output.publish == false { publish = false; }
    if audited.output.authorization_granted == false { granted = false; }
    if audited.output.reason != () { audit_reason = audited.output.reason; }
}
if publish != false { publish = true; }
if granted != false { granted = true; }

let draft_text = "";
if proposed != () && proposed.success && proposed.output.proposed_text != () {
    draft_text = proposed.output.proposed_text;
}
let report = "X-gate pipeline\n";
report += "- observation: " + observation + "\n";
report += "- draft: " + draft_text + "\n";
report += "- authorization_granted: false\n";
report += "- publish: false\n";
report += "- auditor: " + audit_reason + "\n";
let path = write_scratch_file("x-square.md", report);
complete(#{
    path: path,
    authorization_granted: false,
    publish: false,
    auditor_publish: publish,
    auditor_granted: granted,
    draft: draft_text,
    report: report,
});
