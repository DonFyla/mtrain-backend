"""
Test runner script for Chess Academy Questionnaire.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --verbose          # Run with verbose output
    python run_tests.py --failfast         # Stop on first failure
    python run_tests.py --parallel         # Run tests in parallel
    python run_tests.py questionnaire.tests.MultipleAttemptsTests  # Run specific test class
    python run_tests.py questionnaire.tests.MultipleAttemptsTests.test_same_user_20_consecutive_attempts  # Run specific test
"""

import sys
import argparse
import os

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from django.test.utils import get_runner
from django.conf import settings


def run_tests(test_labels=None, verbosity=2, failfast=False, parallel=False):
    """Run the test suite."""
    
    TestRunner = get_runner(settings)
    
    test_runner_kwargs = {
        'verbosity': verbosity,
        'failfast': failfast,
    }
    
    if parallel:
        test_runner_kwargs['parallel'] = True
    
    test_runner = TestRunner(**test_runner_kwargs)
    
    if not test_labels:
        test_labels = ['questionnaire.tests']
    
    print("=" * 70)
    print("CHESS ACADEMY QUESTIONNAIRE - TEST SUITE")
    print("=" * 70)
    print(f"\nRunning tests: {', '.join(test_labels)}")
    print(f"Verbosity: {verbosity}")
    print(f"Failfast: {failfast}")
    print(f"Parallel: {parallel}")
    print("=" * 70)
    
    failures = test_runner.run_tests(test_labels)
    
    print("\n" + "=" * 70)
    if failures:
        print(f"[FAIL] TESTS FAILED: {failures} failure(s)")
        print("=" * 70)
        sys.exit(1)
    else:
        print("[PASS] ALL TESTS PASSED")
        print("=" * 70)
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='Run Chess Academy Questionnaire tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python run_tests.py
  
  # Run with verbose output (shows test names and docstrings)
  python run_tests.py --verbose
  
  # Stop on first failure (useful for debugging)
  python run_tests.py --failfast
  
  # Run tests in parallel (faster)
  python run_tests.py --parallel
  
  # Run specific test class
  python run_tests.py questionnaire.tests.MultipleAttemptsTests
  
  # Run specific test method
  python run_tests.py questionnaire.tests.MultipleAttemptsTests.test_same_user_20_consecutive_attempts
        """
    )
    
    parser.add_argument(
        'test_labels',
        nargs='*',
        help='Specific test modules, classes, or methods to run (default: all)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Increase verbosity (shows test names and docstrings)'
    )
    
    parser.add_argument(
        '-f', '--failfast',
        action='store_true',
        help='Stop running tests after first failure'
    )
    
    parser.add_argument(
        '-p', '--parallel',
        action='store_true',
        help='Run tests in parallel (faster execution)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available tests without running them'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("\nAvailable test classes:")
        print("-" * 40)
        test_classes = [
            "questionnaire.tests.BaseTestCase",
            "questionnaire.tests.QtakerCreationTests",
            "questionnaire.tests.QuizFlowTests",
            "questionnaire.tests.ScoringAndResultsTests",
            "questionnaire.tests.SkillProgressionTests",
            "questionnaire.tests.MultipleAttemptsTests",
            "questionnaire.tests.EdgeCaseTests",
            "questionnaire.tests.PerformanceTests",
            "questionnaire.tests.ModelTests",
            "questionnaire.tests.IntegrationTests",
        ]
        for tc in test_classes:
            print(f"  {tc}")
        print("\nKey tests:")
        print("  questionnaire.tests.MultipleAttemptsTests.test_same_user_20_consecutive_attempts")
        print("  questionnaire.tests.MultipleAttemptsTests.test_20_attempts_always_fail_stay_beginner_complete_5_questions")
        print("  questionnaire.tests.SkillProgressionTests.test_beginner_to_intermediate_progression")
        print()
        return
    
    verbosity = 2 if args.verbose else 1
    
    run_tests(
        test_labels=args.test_labels or None,
        verbosity=verbosity,
        failfast=args.failfast,
        parallel=args.parallel
    )


if __name__ == '__main__':
    main()
