async () => {
  if (location.protocol !== 'https:' || location.hostname !== 'www.xometry.com' ||
      !location.pathname.startsWith('/quoting/')) return {identity_match:false, reason:'WRONG_REFERENCE_PAGE'};
  try {
    const r = await fetch('https://api.xometry.com/v2/users/me', {
      credentials:'include', redirect:'error', headers:{Accept:'application/json'},
      signal:AbortSignal.timeout(3000)
    });
    if (!r.ok) return {identity_match:false, identity_available:false};
    const body = await r.json(), user = body.data || body.user || body;
    const values = ['email_address','email'].map(k=>user?.[k])
      .filter(v=>typeof v==='string' && v.trim());
    let matched = false;
    for (const value of values) {
      const bytes = await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value.trim().toLowerCase()));
      const digest = [...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,'0')).join('');
      matched ||= digest === "b5adba0058e749321b6f3306b1f7f15544335b5a6e1cf338c772fd0017567842";
    }
    return {identity_match:matched, identity_available:values.length>0};
  } catch {return {identity_match:false, identity_available:false};}
}