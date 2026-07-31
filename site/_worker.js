import dataset from "./meaning/echoes.json" with {type: "json"};
import {createPagesWorker} from "./meaning/cloudflare.mjs";

export default createPagesWorker(dataset);
