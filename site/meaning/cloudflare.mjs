import {createMeaningHandler} from "./http.mjs";

function createPagesWorker(dataset) {
  const handleMeaning = createMeaningHandler(dataset);

  return {
    async fetch(request, env) {
      const pathname = new URL(request.url).pathname;
      if (pathname === "/api/meaning/echo" || pathname === "/api/meaning/echo/") {
        return handleMeaning(request);
      }
      return env.ASSETS.fetch(request);
    },
  };
}

export {createPagesWorker};
