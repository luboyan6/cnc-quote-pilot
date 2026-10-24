// Validation only: this fixture cannot reach a business or provider API.
export function request() {
  throw new Error('Network disabled in local UI fixture');
}
