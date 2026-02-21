"""
Management command to run critical tests for the Chess Academy Questionnaire.

Usage:
    python manage.py test_critical
    python manage.py test_critical --quick  # Skip the 20-attempts test
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run critical tests for the Chess Academy Questionnaire'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Skip the 20-consecutive-attempts test (faster)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            '=' * 70
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            'CHESS ACADEMY - CRITICAL TESTS'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            '=' * 70
        ))
        self.stdout.write('')
        
        verbosity = 2 if options['verbose'] else 1
        
        # Critical tests to run
        critical_tests = [
            'questionnaire.tests.QtakerCreationTests',
            'questionnaire.tests.QuizFlowTests',
            'questionnaire.tests.ScoringAndResultsTests',
            'questionnaire.tests.SkillProgressionTests',
        ]
        
        if not options['quick']:
            critical_tests.append(
                'questionnaire.tests.MultipleAttemptsTests.test_same_user_20_consecutive_attempts'
            )
            critical_tests.append(
                'questionnaire.tests.MultipleAttemptsTests.test_rapid_fire_same_user_no_state_leak'
            )
        
        self.stdout.write(f"Running {len(critical_tests)} critical test classes...")
        self.stdout.write('')
        
        for test in critical_tests:
            self.stdout.write(f"  → {test}")
        
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            '-' * 70
        ))
        
        try:
            call_command(
                'test',
                *critical_tests,
                verbosity=verbosity,
                failfast=True
            )
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(
                '✅ ALL CRITICAL TESTS PASSED'
            ))
        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(
                f'❌ TESTS FAILED: {str(e)}'
            ))
            raise
