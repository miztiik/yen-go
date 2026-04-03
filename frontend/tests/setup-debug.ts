// Minimal setup: just afterEach + vi using globals
// @ts-expect-error globals
afterEach(() => {
  console.log('afterEach executed');
});
