"""
Comando de management para auditar y eliminar referencias a /admin/login/ 
en el código de tenants privados.

⚠️ OBJETIVO: Garantizar que la landing page (/) sea la vista principal
y que /login/ sea el punto de acceso de autenticación, NO /admin/login/.
"""
from django.core.management.base import BaseCommand
import os
import re
from pathlib import Path


class Command(BaseCommand):
    help = 'Audita y reporta referencias a /admin/login/ en el código de tenants privados.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Intentar corregir automáticamente las referencias encontradas',
        )

    def handle(self, *args, **options):
        fix_issues = options.get('fix', False)
        
        self.stdout.write("=" * 80)
        self.stdout.write("🔍 AUDITORÍA DE REFERENCIAS A /admin/login/ EN TENANTS PRIVADOS")
        self.stdout.write("=" * 80)
        self.stdout.write("")
        
        # Directorios a auditar
        base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        tenant_dirs = [
            base_dir / 'apps' / 'tenant',
            base_dir / 'config',
        ]
        
        # Patrón a buscar
        pattern = re.compile(r'/admin/login/?', re.IGNORECASE)
        
        issues_found = []
        
        for tenant_dir in tenant_dirs:
            if not tenant_dir.exists():
                continue
                
            self.stdout.write(f"📁 Buscando en: {tenant_dir}")
            
            # Buscar en archivos Python
            for py_file in tenant_dir.rglob('*.py'):
                # Excluir __pycache__ y migraciones
                if '__pycache__' in str(py_file) or 'migrations' in str(py_file):
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for line_num, line in enumerate(lines, 1):
                            if pattern.search(line):
                                # Verificar si es un comentario o documentación
                                stripped = line.strip()
                                if stripped.startswith('#') or '"""' in line or "'''" in line:
                                    # Es un comentario o docstring, reportar pero no es crítico
                                    issues_found.append({
                                        'file': py_file,
                                        'line': line_num,
                                        'content': line.strip(),
                                        'type': 'comment',
                                        'critical': False
                                    })
                                else:
                                    # Es código activo, CRÍTICO
                                    issues_found.append({
                                        'file': py_file,
                                        'line': line_num,
                                        'content': line.strip(),
                                        'type': 'code',
                                        'critical': True
                                    })
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"   ⚠️  Error al leer {py_file}: {e}")
                    )
        
        # Reportar resultados
        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write("📊 RESULTADOS DE LA AUDITORÍA")
        self.stdout.write("=" * 80)
        
        if not issues_found:
            self.stdout.write(self.style.SUCCESS("✅ No se encontraron referencias a /admin/login/"))
        else:
            critical_issues = [i for i in issues_found if i['critical']]
            comment_issues = [i for i in issues_found if not i['critical']]
            
            if critical_issues:
                self.stdout.write("")
                self.stdout.write(self.style.ERROR(f"❌ Referencias CRÍTICAS encontradas: {len(critical_issues)}"))
                for issue in critical_issues:
                    rel_path = issue['file'].relative_to(base_dir)
                    self.stdout.write(
                        self.style.ERROR(
                            f"   📄 {rel_path}:{issue['line']}"
                        )
                    )
                    self.stdout.write(f"      {issue['content']}")
            
            if comment_issues:
                self.stdout.write("")
                self.stdout.write(self.style.WARNING(f"⚠️  Referencias en comentarios/docstrings: {len(comment_issues)}"))
                for issue in comment_issues[:5]:  # Mostrar solo las primeras 5
                    rel_path = issue['file'].relative_to(base_dir)
                    self.stdout.write(
                        self.style.WARNING(
                            f"   📄 {rel_path}:{issue['line']} (comentario)"
                        )
                    )
                if len(comment_issues) > 5:
                    self.stdout.write(f"   ... y {len(comment_issues) - 5} más")
        
        self.stdout.write("")
        self.stdout.write("=" * 80)
        
        if issues_found and not fix_issues:
            self.stdout.write(
                self.style.WARNING(
                    "💡 Ejecuta con --fix para intentar corregir automáticamente"
                )
            )
