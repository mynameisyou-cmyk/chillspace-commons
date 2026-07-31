import {createRequire} from "node:module";
import {
  MAX_BODY_BYTES,
  createMeaningHandler,
} from "../../meaning/http.mjs";

const require = createRequire(import.meta.url);
const dataset = require("../../meaning/echoes.json");
const handle = createMeaningHandler(dataset);

export {handle, MAX_BODY_BYTES};

export default {
  fetch: handle,
};
