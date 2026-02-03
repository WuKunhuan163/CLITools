#!/bin/bash

URL="https://fontsgeek.com/fonts/arnhem-blond/download"
REFERER="https://fontsgeek.com/fonts/arnhem-blond"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

echo "--- Attempt 1: Direct curl with Referer ---"
curl -L -o "tool/READ/tmp/attempt1.zip" -e "$REFERER" -A "$UA" "$URL"
echo "Size: $(wc -c < tool/READ/tmp/attempt1.zip)"
head -c 50 tool/READ/tmp/attempt1.zip

echo -e "\n--- Attempt 2: Session based (cookies) ---"
curl -L -c "tool/READ/tmp/cookies.txt" -A "$UA" "$REFERER" > /dev/null
curl -L -b "tool/READ/tmp/cookies.txt" -e "$REFERER" -A "$UA" -o "tool/READ/tmp/attempt2.zip" "$URL"
echo "Size: $(wc -c < tool/READ/tmp/attempt2.zip)"
head -c 50 tool/READ/tmp/attempt2.zip

echo -e "\n--- Attempt 3: POST method as seen in form ---"
# Get CSRF
CSRF=$(grep -o 'name="csrfmiddlewaretoken" value="[^"]*"' tool/READ/tmp/arnhem_page.html | cut -d'"' -f4)
echo "Using CSRF: $CSRF"
curl -L -b "tool/READ/tmp/cookies.txt" -e "$REFERER" -A "$UA" \
     -d "csrfmiddlewaretoken=$CSRF" -d "method=zip" \
     -o "tool/READ/tmp/attempt3.zip" "https://fontsgeek.com/fonts/Arnhem-Blond"
echo "Size: $(wc -c < tool/READ/tmp/attempt3.zip)"
head -c 50 tool/READ/tmp/attempt3.zip

