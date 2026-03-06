#!/usr/bin/env python3
"""
MIGRATION UTILITIES - Convert Existing Data to Coordinate Encoding
==================================================================
Coordinate Lookup Encoding System - Phase 4

Utilities for migrating from microscopic line storage to coordinate encoding
Includes validation, rollback, and compression ratio checking

Dr. Martinez (Migration Lead)
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime


class MigrationValidator:
    """
    Validates migration from microscopic lines to coordinate encoding
    Ensures data integrity and compression improvements
    """
    
    def __init__(self):
        """Initialize migration validator"""
        self.validation_results = []
        
        print("🔄 MIGRATION VALIDATOR INITIALIZED")
    
    def validate_word_migration(self, word: str, old_data: Dict, new_data: Dict) -> Dict[str, Any]:
        """
        Validate migration of single word
        
        Args:
            word: Word being migrated
            old_data: Old microscopic line data
            new_data: New coordinate-encoded data
        
        Returns:
            Dict with validation results
        """
        result = {
            'word': word,
            'passed': False,
            'old_size': 0,
            'new_size': 0,
            'vertical_size': 0,
            'horizontal_size': 0,
            'compression_improvement': 0.0,
            'reconstruction_match': False,
            'errors': [],
            'validation_guards': []
        }
        
        try:
            # Extract old positions
            if 'internal_lines' in old_data:
                old_positions = [line['line_position'] for line in old_data['internal_lines']]
                # Calculate old size in BYTES (not positions)
                # Old format: SINGLE-DIMENSION (vertical only) = 1 integer per position = 4 bytes
                # Legacy storage only had line positions, not horizontal coordinates
                result['old_size'] = len(old_data['internal_lines']) * 4
            elif 'original_positions' in old_data:
                old_positions = old_data['original_positions']
                # Assume single-dimension legacy format: 1 integer = 4 bytes per position
                result['old_size'] = len(old_positions) * 4
            else:
                result['errors'].append("Cannot extract old positions")
                return result
            
            # Extract new positions and dimension-specific sizes
            if 'original_positions' in new_data:
                new_positions_full = new_data['original_positions']
                # Extract just line positions from dual-dimension format for comparison
                # New format: [{'line': X, 'horizontal': Y}, ...]
                # Extract 'line' values to compare with old format
                new_positions = [pos['line'] if isinstance(pos, dict) else pos 
                                for pos in new_positions_full]
                # Extract dimension-specific sizes for validation guards
                result['vertical_size'] = new_data.get('vertical_encoded_size', 0)
                result['horizontal_size'] = new_data.get('horizontal_encoded_size', 0)
                result['new_size'] = new_data.get('encoded_size', 0)
            else:
                result['errors'].append("Cannot extract new positions")
                return result
            
            # Verify reconstruction (compare line positions only, as horizontal is new in dual-dimension)
            old_sorted = sorted(old_positions)
            new_sorted = sorted(new_positions)
            result['reconstruction_match'] = old_sorted == new_sorted
            
            if not result['reconstruction_match']:
                result['errors'].append(f"Position mismatch: {old_sorted} != {new_sorted}")
            
            # Calculate compression improvement
            if result['old_size'] > 0:
                result['compression_improvement'] = (
                    (result['old_size'] - result['new_size']) / result['old_size'] * 100
                )
            
            # TWO-TIER VALIDATION GUARDS (enforce in validator, not just tests)
            
            # Guard #1: Ratio Cap - new size must be ≤125% of old size
            ratio = result['new_size'] / result['old_size'] if result['old_size'] > 0 else 0
            if ratio <= 1.25:
                result['validation_guards'].append(f"Ratio cap PASS: {ratio:.2f}x ≤ 1.25x")
            else:
                result['validation_guards'].append(f"Ratio cap FAIL: {ratio:.2f}x > 1.25x")
                result['errors'].append(f"Size blow-up: {result['new_size']} bytes = {ratio:.2f}x > 1.25x limit")
            
            # Guard #2: Vertical Compression - vertical encoding must save ≥20% vs raw vertical
            if result['vertical_size'] > 0 and result['old_size'] > 0:
                vertical_ratio = result['vertical_size'] / result['old_size']
                if vertical_ratio <= 0.8:
                    result['validation_guards'].append(f"Vertical savings PASS: {vertical_ratio:.2f}x ≤ 0.8x (≥20% savings)")
                else:
                    savings_pct = (1 - vertical_ratio) * 100
                    result['validation_guards'].append(f"Vertical savings FAIL: {vertical_ratio:.2f}x > 0.8x ({savings_pct:.0f}% < 20% minimum)")
                    result['errors'].append(f"Vertical encoding {result['vertical_size']} bytes fails ≥20% savings requirement (vs {result['old_size']} bytes raw)")
            
            # Overall pass/fail (includes validation guard checks)
            result['passed'] = result['reconstruction_match'] and len(result['errors']) == 0
            
        except Exception as e:
            result['errors'].append(f"Validation error: {str(e)}")
        
        self.validation_results.append(result)
        return result
    
    def validate_batch(self, old_data: Dict, new_data: Dict) -> Dict[str, Any]:
        """
        Validate batch migration
        
        Args:
            old_data: Dict of old word data
            new_data: Dict of new coordinate-encoded data
        
        Returns:
            Overall validation summary
        """
        results = []
        
        for word in old_data.keys():
            if word in new_data:
                result = self.validate_word_migration(
                    word,
                    old_data[word],
                    new_data[word]
                )
                results.append(result)
            else:
                results.append({
                    'word': word,
                    'passed': False,
                    'errors': ['Word missing in new data']
                })
        
        # Calculate summary
        total = len(results)
        passed = sum(1 for r in results if r.get('passed', False))
        failed = total - passed
        
        total_old_size = sum(r.get('old_size', 0) for r in results)
        total_new_size = sum(r.get('new_size', 0) for r in results)
        overall_compression = (
            (total_old_size - total_new_size) / total_old_size * 100
            if total_old_size > 0 else 0
        )
        
        return {
            'total_words': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / total if total > 0 else 0,
            'total_old_size': total_old_size,
            'total_new_size': total_new_size,
            'compression_improvement': overall_compression,
            'results': results
        }
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        Generate validation report
        
        Args:
            output_file: Optional path to save report
        
        Returns:
            Report string
        """
        if not self.validation_results:
            return "No validation results available"
        
        report_lines = [
            "=" * 70,
            "COORDINATE ENCODING MIGRATION VALIDATION REPORT",
            "=" * 70,
            f"Generated: {datetime.now().isoformat()}",
            "",
            "SUMMARY:",
            f"  Total validations: {len(self.validation_results)}",
            f"  Passed: {sum(1 for r in self.validation_results if r['passed'])}",
            f"  Failed: {sum(1 for r in self.validation_results if not r['passed'])}",
            "",
            "COMPRESSION IMPROVEMENT:",
        ]
        
        total_old = sum(r['old_size'] for r in self.validation_results)
        total_new = sum(r['new_size'] for r in self.validation_results)
        improvement = (total_old - total_new) / total_old * 100 if total_old > 0 else 0
        
        report_lines.extend([
            f"  Total old size: {total_old}",
            f"  Total new size: {total_new}",
            f"  Overall improvement: {improvement:.2f}%",
            "",
            "FAILED VALIDATIONS:"
        ])
        
        failed = [r for r in self.validation_results if not r['passed']]
        if failed:
            for r in failed:
                report_lines.append(f"  - {r['word']}: {', '.join(r['errors'])}")
        else:
            report_lines.append("  None - all validations passed! ✅")
        
        report_lines.append("=" * 70)
        
        report = "\n".join(report_lines)
        
        if output_file:
            Path(output_file).write_text(report)
            print(f"📄 Report saved to: {output_file}")
        
        return report


class DataMigrator:
    """
    Migrates data from microscopic line format to coordinate encoding
    """
    
    def __init__(self):
        """Initialize data migrator"""
        from .scanner_integration import ScannerCoordinateIntegration
        
        self.integrator = ScannerCoordinateIntegration()
        self.validator = MigrationValidator()
        
        print("🔄 DATA MIGRATOR INITIALIZED")
    
    def migrate_scanner_output(self, old_scanner_data: Dict) -> Tuple[Dict, Dict]:
        """
        Migrate complete scanner output to coordinate encoding
        
        Args:
            old_scanner_data: Old scanner output with microscopic lines
        
        Returns:
            Tuple of (new_data, validation_report)
        """
        new_data = {}
        
        # Extract word positions from old format
        for word, word_info in old_scanner_data.items():
            # Convert microscopic line format to position list
            if 'internal_lines' in word_info:
                positions = [
                    {'line': line['line_position'], 'horizontal': 0}
                    for line in word_info['internal_lines']
                ]
            elif 'positions' in word_info:
                positions = word_info['positions']
            else:
                continue
            
            # Encode using coordinate system
            new_data[word] = self.integrator.encode_word_positions(word, positions)
        
        # Validate migration
        validation_report = self.validator.validate_batch(old_scanner_data, new_data)
        
        return new_data, validation_report
    
    def create_backup(self, data: Dict, backup_path: str):
        """
        Create backup of data before migration
        
        Args:
            data: Data to backup
            backup_path: Path to save backup
        """
        backup_file = Path(backup_path)
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'hash': hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        }
        
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        print(f"💾 Backup created: {backup_file}")
        return backup_file
    
    def rollback(self, backup_path: str) -> Dict:
        """
        Rollback to backup data
        
        Args:
            backup_path: Path to backup file
        
        Returns:
            Restored data
        """
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        # Verify hash
        data = backup_data['data']
        expected_hash = backup_data['hash']
        actual_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        
        if expected_hash != actual_hash:
            raise ValueError("Backup data integrity check failed")
        
        print(f"🔙 Rollback successful from: {backup_file}")
        return data


if __name__ == "__main__":
    # Self-test
    print("🔄 MIGRATION UTILITIES - Self Test")
    print("=" * 50)
    
    # Create test data
    old_data = {
        'the': {
            'internal_lines': [
                {'line_position': 1, 'angle': 0},
                {'line_position': 5, 'angle': 72},
                {'line_position': 10, 'angle': 144}
            ]
        },
        'and': {
            'internal_lines': [
                {'line_position': 2, 'angle': 0},
                {'line_position': 7, 'angle': 180}
            ]
        }
    }
    
    # Migrate
    migrator = DataMigrator()
    new_data, validation = migrator.migrate_scanner_output(old_data)
    
    print("\nMigration validation:")
    print(f"  Total words: {validation['total_words']}")
    print(f"  Passed: {validation['passed']}")
    print(f"  Failed: {validation['failed']}")
    print(f"  Pass rate: {validation['pass_rate'] * 100:.1f}%")
    print(f"  Compression improvement: {validation['compression_improvement']:.2f}%")
    
    # Generate report
    print("\n" + migrator.validator.generate_report())
    
    print("\n✅ Migration utilities tests complete")
