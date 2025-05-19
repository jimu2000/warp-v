This program can help you filter out the IP with the lowest latency from Cloudflare's IP pool for WARP connection optimization. The program automatically obtains IP segments from Cloudflare, randomly selects a portion of IPs for testing, and then sorts them according to response time to select the best IP list.
Main features include:
1. Automatically obtain IP segments from Cloudflare
2. Multi-threaded testing of IP connection speed and availability
3. Results are sorted by response time
4. Save and load test results
5. Detailed logging


Main module description
WARPIPSelector class: encapsulates all core functions
load_cloudflare_ips(): obtain and parse Cloudflare's IP segments
test_single_ip(): test the connectivity and response time of a single IP
run_tests(): perform tests on all IPs
get_best_ips(): obtain the best IPs
save_to_file() and load_from_file(): manage the storage of test results
