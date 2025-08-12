# utils/fetch_logos.py
import os, time, requests, certifi

ESPN = "https://a.espncdn.com/i/teamlogos/nfl/500/{code}.png"

CODES = [
    "ari","atl","bal","buf","car","chi","cin","cle","dal","den","det","gb","hou","ind","jac","kc",
    "lv","lac","lar","mia","min","ne","no","nyg","nyj","phi","pit","sea","sf","tb","ten","wsh"
]

def download(url: str, dst: str, attempts: int = 3) -> bool:
    # First try with proper CA bundle
    for i in range(attempts):
        try:
            with requests.get(url, timeout=15, stream=True, verify=certifi.where()) as r:
                r.raise_for_status()
                with open(dst, "wb") as f:
                    for chunk in r.iter_content(8192):
                        if chunk:
                            f.write(chunk)
            return True
        except Exception as e:
            print(f"  attempt {i+1}/{attempts} ({type(e).__name__}): {e}")
            time.sleep(0.7)

    # LAST RESORT: try without verification (not ideal, but unblocks local caching)
    print("  falling back to verify=False (temporary workaround)")
    try:
        with requests.get(url, timeout=15, stream=True, verify=False) as r:  # noqa: S501
            r.raise_for_status()
            with open(dst, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"  final failure: {e}")
        return False

def main():
    root = os.path.dirname(os.path.dirname(__file__))  # utils -> project root
    logos_dir = os.path.join(root, "static", "logos")
    os.makedirs(logos_dir, exist_ok=True)

    for code in CODES:
        fn = f"{code.upper()}.png"
        dst = os.path.join(logos_dir, fn)
        if os.path.exists(dst):
            print(f"✓ {fn} exists")
            continue
        url = ESPN.format(code=code)
        print(f"↓ {code} -> {fn}")
        ok = download(url, dst)
        if not ok:
            print(f"!! failed {code}")

if __name__ == "__main__":
    main()
