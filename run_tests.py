#!/usr/bin/env python3
"""
Runner para testes do Sistema GELADEIRA
Executa todos os testes e produz relatório consolidado
"""
import os
import sys
import unittest
import logging
import argparse
import time
from datetime import datetime
from pathlib import Path

def setup_logging(log_dir=None):
    """Configure logging with optional directory"""
    if log_dir:
        Path(log_dir).mkdir(exist_ok=True)
        log_path = Path(log_dir) / f"test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    else:
        log_path = f"test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(str(log_path)),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def run_tests(pattern='test_*.py', start_dir='tests', verbosity=2, failfast=False):
    """Run tests with specified parameters"""
    # Adicionar diretório raiz ao path para importações relativas funcionarem
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Descobrir e executar testes
    start_time = time.time()
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(start_dir, pattern=pattern)
    
    # Executar testes
    result = unittest.TextTestRunner(verbosity=verbosity, failfast=failfast).run(test_suite)
    elapsed_time = time.time() - start_time
    
    return result, elapsed_time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Runner para testes do Sistema GELADEIRA')
    parser.add_argument('--pattern', default='test_*.py', help='Padrão para encontrar arquivos de teste')
    parser.add_argument('--start-dir', default='tests', help='Diretório onde procurar os testes')
    parser.add_argument('--log-dir', help='Diretório para armazenar logs')
    parser.add_argument('--failfast', action='store_true', help='Parar nos primeiros testes que falharem')
    parser.add_argument('-v', '--verbosity', type=int, choices=[0, 1, 2], default=2, 
                        help='Nível de detalhamento (0-2)')
    
    args = parser.parse_args()
    logger = setup_logging(args.log_dir)
    
    print("=" * 80)
    print(" INICIANDO TESTES DO SISTEMA GELADEIRA ")
    print("=" * 80)
    
    # Executar testes com os argumentos fornecidos
    result, elapsed_time = run_tests(
        pattern=args.pattern, 
        start_dir=args.start_dir,
        verbosity=args.verbosity,
        failfast=args.failfast
    )
    
    # Resumo dos resultados
    print("\n" + "=" * 80)
    print(f"Total de Testes: {result.testsRun}")
    print(f"Falhas: {len(result.failures)}")
    print(f"Erros: {len(result.errors)}")
    print(f"Testes Pulados: {len(result.skipped)}")
    print(f"Tempo de execução: {elapsed_time:.2f} segundos")
    print("=" * 80)
    
    # Definir código de saída baseado no resultado
    sys.exit(0 if result.wasSuccessful() else 1)
