# test_l_menthol.py
"""
Test script for L-MENTHOL to verify the LLM is actually processing instructions
and not just memorizing PETROLATUM examples.
"""
import requests
import json
import os
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_l_menthol_noael():
    """Test NOAEL update for L-MENTHOL"""
    print_section("TEST 1: L-MENTHOL NOAEL Update")
    
    instruction = """
    For L-MENTHOL:
    - Set NOAEL to 200 mg/kg bw/day
    - Source: OECD SIDS MENTHOLS UNEP PUBLICATIONS
    - Reference: https://hpvchemicals.oecd.org/ui/handler.axd?id=463ce644-e5c8-42e8-962d-3a917f32ab90
    """
    
    print("📝 Instruction:")
    print(instruction)
    print("\n⏳ Sending request...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/edit",
            json={
                "inci_name": "L-MENTHOL",
                "instruction": instruction
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✅ Status: {response.status_code}")
            print(f"✅ INCI: {result.get('inci')}")
            print(f"✅ Response: {result.get('raw_response')[:150]}...")
            
            # Verify the update
            updated_json = result.get('updated_json', {})
            
            # Check INCI name
            if updated_json.get('inci') == 'L-MENTHOL':
                print("\n✅ INCI correctly updated to L-MENTHOL")
            else:
                print(f"\n❌ INCI incorrect: {updated_json.get('inci')}")
            
            # Check NOAEL
            noael_data = updated_json.get('NOAEL', [])
            if noael_data:
                print(f"\n✅ NOAEL updated: {len(noael_data)} entry/entries")
                
                # Verify the first NOAEL entry
                first_noael = noael_data[0]
                print("\n📊 NOAEL Details:")
                print(f"   Value: {first_noael.get('value')} {first_noael.get('unit')}")
                print(f"   Source: {first_noael.get('source')}")
                print(f"   Type: {first_noael.get('type')}")
                
                # Validation checks
                checks = {
                    "Value is 200": first_noael.get('value') == 200,
                    "Unit is mg/kg bw/day": first_noael.get('unit') == 'mg/kg bw/day',
                    "Source contains OECD/SIDS": 'oecd' in first_noael.get('source', '').lower() or 'sids' in first_noael.get('source', '').lower(),
                    "Type is NOAEL": first_noael.get('type') == 'NOAEL'
                }
                
                print("\n🔍 Validation Results:")
                for check, passed in checks.items():
                    status = "✅" if passed else "❌"
                    print(f"   {status} {check}")
                
                # Check if it's not copying PETROLATUM data
                if first_noael.get('value') == 800:
                    print("\n⚠️  WARNING: Value is 800 (same as PETROLATUM example) - possible cheating!")
                
            else:
                print("\n❌ NOAEL not updated!")
            
            # Check repeated_dose_toxicity
            rdt_data = updated_json.get('repeated_dose_toxicity', [])
            if rdt_data:
                print(f"\n✅ Repeated dose toxicity updated: {len(rdt_data)} entry/entries")
                
                # Check reference
                first_rdt = rdt_data[0]
                ref = first_rdt.get('reference', {})
                print(f"\n📚 Reference:")
                print(f"   Title: {ref.get('title', 'N/A')}")
                print(f"   Link: {ref.get('link', 'N/A')}")
                
                # Verify link contains the OECD URL
                if 'oecd.org' in ref.get('link', '').lower():
                    print("   ✅ Reference link contains OECD domain")
                else:
                    print("   ⚠️  Reference link doesn't contain OECD domain")
                
            else:
                print("\n⚠️  Repeated dose toxicity not updated")
            
            return True
            
        else:
            print(f"\n❌ Request failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out (LLM processing took too long)")
        return False
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection failed! Is the server running?")
        print("   Start with: python run.py")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def test_verify_current_data():
    """Verify the data was actually saved"""
    print_section("TEST 2: Verify Saved Data")
    
    try:
        response = requests.get(f"{BASE_URL}/api/current")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"Current INCI: {data.get('inci')}")
            
            if data.get('inci') == 'L-MENTHOL':
                print("✅ INCI is L-MENTHOL (correct)")
            else:
                print(f"❌ INCI is {data.get('inci')} (expected L-MENTHOL)")
            
            noael = data.get('NOAEL', [])
            if noael and noael[0].get('value') == 200:
                print("✅ NOAEL value is 200 (correct)")
            else:
                print(f"❌ NOAEL value is {noael[0].get('value') if noael else 'missing'}")
            
            return True
        else:
            print(f"❌ Failed to get current data: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_check_file_persistence():
    """Check if data was written to file correctly"""
    print_section("TEST 3: File Persistence Check")
    
    possible_paths = [
        "./data/toxicity_data_template.json",
        "./toxicity_data_template.json",
    ]
    
    for filepath in possible_paths:
        if os.path.exists(filepath):
            print(f"✅ Found file: {filepath}\n")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                print(f"File INCI: {data.get('inci')}")
                
                # Detailed check
                noael = data.get('NOAEL', [])
                if noael:
                    print(f"\nNOAEL in file:")
                    print(json.dumps(noael[0], indent=2, ensure_ascii=False))
                    
                    if noael[0].get('value') == 200:
                        print("\n✅ File contains correct NOAEL value (200)")
                    else:
                        print(f"\n❌ File NOAEL value is {noael[0].get('value')} (expected 200)")
                else:
                    print("\n❌ No NOAEL data in file")
                
                return True
                
            except Exception as e:
                print(f"❌ Error reading file: {e}")
                return False
    
    print("❌ File not found in any expected location")
    return False

def test_different_substance_dap():
    """Test with a different update type (DAP instead of NOAEL) to ensure versatility"""
    print_section("TEST 4: Different Update Type - DAP")
    
    instruction = """
    For L-MENTHOL:
    - Update DAP (Dermal Absorption Percentage) to 5%
    - Based on lipophilic nature and molecular weight considerations
    - Source: Expert assessment
    """
    
    print("📝 Testing DAP update (different from NOAEL)...")
    print(instruction)
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/edit",
            json={
                "inci_name": "L-MENTHOL",
                "instruction": instruction
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            updated_json = result.get('updated_json', {})
            
            dap = updated_json.get('DAP', [])
            if dap and dap[0].get('value') == 5:
                print("\n✅ DAP correctly updated to 5%")
                print(f"   DAP entry: {json.dumps(dap[0], indent=2, ensure_ascii=False)}")
                return True
            else:
                print(f"\n❌ DAP not correctly updated. Value: {dap[0].get('value') if dap else 'missing'}")
                return False
        else:
            print(f"\n❌ Request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_reset_for_clean_slate():
    """Reset the JSON to ensure we're starting fresh"""
    print_section("SETUP: Resetting to Template")
    
    try:
        response = requests.post(f"{BASE_URL}/api/reset")
        if response.status_code == 200:
            print("✅ Successfully reset to template")
            return True
        else:
            print(f"❌ Reset failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def compare_with_petrolatum():
    """Compare L-MENTHOL results with PETROLATUM to ensure no copying"""
    print_section("TEST 5: Anti-Cheating Check")
    
    print("Checking if model is copying PETROLATUM example data...\n")
    
    try:
        response = requests.get(f"{BASE_URL}/api/current")
        if response.status_code == 200:
            data = response.json()
            
            noael = data.get('NOAEL', [])
            if not noael:
                print("⚠️  No NOAEL data to check")
                return True
            
            first_noael = noael[0]
            
            # Check for PETROLATUM-specific values
            petrolatum_indicators = {
                "Value is 800 (PETROLATUM)": first_noael.get('value') == 800,
                "Experiment target is Rats (PETROLATUM)": first_noael.get('experiment_target') == 'Rats',
                "Study duration is 90-day (PETROLATUM)": first_noael.get('study_duration') == '90-day',
            }
            
            cheating_detected = False
            print("🔍 Checking for PETROLATUM data copying:")
            for indicator, detected in petrolatum_indicators.items():
                if detected:
                    print(f"   ❌ {indicator} - POSSIBLE CHEATING!")
                    cheating_detected = True
                else:
                    print(f"   ✅ {indicator} - OK")
            
            if not cheating_detected:
                print("\n✅ No evidence of copying PETROLATUM data")
                return True
            else:
                print("\n⚠️  WARNING: Model may be copying example data!")
                return False
        else:
            print(f"❌ Failed to get data: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_comprehensive_test():
    """Run all tests in sequence"""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + "  L-MENTHOL COMPREHENSIVE TEST SUITE".center(68) + "█")
    print("█" + "  Testing LLM's ability to process new substances".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)
    
    results = {}
    
    # Test 0: Health check
    print_section("SETUP: Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is healthy")
        else:
            print("❌ Server health check failed")
            print("Please start the server with: python run.py")
            return
    except:
        print("❌ Cannot reach server")
        print("Please start the server with: python run.py")
        return
    
    # Test 0.5: Reset first
    results['reset'] = test_reset_for_clean_slate()
    time.sleep(1)
    
    # Test 1: Main NOAEL update
    results['noael_update'] = test_l_menthol_noael()
    time.sleep(1)
    
    # Test 2: Verify data persistence
    results['verify_data'] = test_verify_current_data()
    time.sleep(1)
    
    # Test 3: File check
    results['file_check'] = test_check_file_persistence()
    time.sleep(1)
    
    # Test 4: Different update type
    results['dap_update'] = test_different_substance_dap()
    time.sleep(1)
    
    # Test 5: Anti-cheating check
    results['anti_cheat'] = compare_with_petrolatum()
    
    # Summary
    print_section("TEST SUMMARY")
    
    total_tests = len([k for k in results.keys() if k != 'reset'])
    passed_tests = sum(1 for k, v in results.items() if k != 'reset' and v)
    
    print(f"Tests Passed: {passed_tests}/{total_tests}\n")
    
    for test_name, passed in results.items():
        if test_name == 'reset':
            continue
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {test_name.replace('_', ' ').title()}")
    
    if passed_tests == total_tests:
        print("\n" + "🎉"*30)
        print("🎉  ALL TESTS PASSED - MODEL IS WORKING CORRECTLY!  🎉")
        print("🎉"*30)
    else:
        print("\n" + "⚠️ "*20)
        print("Some tests failed. Check the details above.")
        print("⚠️ "*20)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Run individual tests
        test_map = {
            'noael': test_l_menthol_noael,
            'verify': test_verify_current_data,
            'file': test_check_file_persistence,
            'dap': test_different_substance_dap,
            'cheat': compare_with_petrolatum,
            'reset': test_reset_for_clean_slate,
        }
        
        test_name = sys.argv[1].lower()
        if test_name in test_map:
            test_map[test_name]()
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(test_map.keys())}")
    else:
        # Run comprehensive test suite
        run_comprehensive_test()