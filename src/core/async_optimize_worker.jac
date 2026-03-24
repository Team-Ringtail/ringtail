"""Background worker entrypoint for async optimization jobs."""

import json;
import os;
import sys;
import traceback;

import from src.api.optimization_requests { run_optimization_request }


def _load_request -> dict {
    request_file = os.environ.get("RINGTAIL_ASYNC_REQUEST_FILE", "");
    if request_file == "" {
        raise ValueError("RINGTAIL_ASYNC_REQUEST_FILE is required");
    }
    with open(request_file, "r") as f {
        return json.loads(f.read());
    }
}


with entry {
    try {
        print("[ringtail_worker] loading request from RINGTAIL_ASYNC_REQUEST_FILE", file=sys.stderr);
        request = _load_request();
        op = str(request.get("operation", "optimize_input"));
        print("[ringtail_worker] starting operation=" + op, file=sys.stderr);
        result = run_optimization_request(request);
        print("[ringtail_worker] optimization finished; emitting JSON result to stdout", file=sys.stderr);
        print(json.dumps(result));
    } except Exception as e {
        failure = {
            "error": "Async worker failed: " + str(e),
            "traceback": traceback.format_exc()
        };
        print(json.dumps(failure));
        raise e;
    }
}
