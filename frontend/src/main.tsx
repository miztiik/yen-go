/**
 * App entry point — delegates to boot().
 *
 * Boot handles: config fetch → Goban init → legacy cleanup → App render.
 * See boot.ts for the 5-step boot sequence.
 *
 * Spec 127: FR-036
 */
import './styles/app.css';
import { boot } from './boot';

void boot();
