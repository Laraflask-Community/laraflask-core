"""
BladePy Template Engine
Laravel Blade-inspired template engine for Python/Flask.
Supports @extends, @section, @yield, @include, @if, @foreach, @csrf, @auth, @guest.
"""

from __future__ import annotations
import re
import os
import hashlib
from typing import Any, Dict, List, Optional


class BladePyEngine:
    """
    BladePy — the Laraflask template engine.

    Compiles BladePy templates (.blade.py) to pure Python/HTML,
    then caches the result for fast rendering.
    """

    DIRECTIVES = {
        r'@extends\([\'"](.+?)[\'"]\)':        '_directive_extends',
        r'@section\([\'"](.+?)[\'"]\)':         '_directive_section_start',
        r'@endsection':                          '_directive_section_end',
        r'@yield\([\'"](.+?)[\'"](?:,\s*[\'"](.+?)[\'"])?\)': '_directive_yield',
        r'@include\([\'"](.+?)[\'"]\s*(?:,\s*(.+?))?\)':      '_directive_include',
        r'@if\((.+?)\)':                         '_directive_if',
        r'@elseif\((.+?)\)':                     '_directive_elseif',
        r'@else':                                '_directive_else',
        r'@endif':                               '_directive_endif',
        r'@unless\((.+?)\)':                     '_directive_unless',
        r'@endunless':                           '_directive_endif',
        r'@foreach\((.+?)\s+as\s+(.+?)\)':      '_directive_foreach',
        r'@endforeach':                          '_directive_endforeach',
        r'@for\((.+?)\)':                        '_directive_for',
        r'@endfor':                              '_directive_endfor',
        r'@while\((.+?)\)':                      '_directive_while',
        r'@endwhile':                            '_directive_endwhile',
        r'@forelse\((.+?)\s+as\s+(.+?)\)':      '_directive_forelse',
        r'@empty':                               '_directive_empty',
        r'@endforelse':                          '_directive_endforelse',
        r'@switch\((.+?)\)':                     '_directive_switch',
        r'@case\((.+?)\)':                       '_directive_case',
        r'@break':                               '_directive_break',
        r'@default':                             '_directive_default',
        r'@endswitch':                           '_directive_endswitch',
        r'@csrf':                                '_directive_csrf',
        r'@method\([\'"](.+?)[\'"]\)':           '_directive_method',
        r'@auth':                                '_directive_auth',
        r'@endauth':                             '_directive_endauth',
        r'@guest':                               '_directive_guest',
        r'@endguest':                            '_directive_endguest',
        r'@can\([\'"](.+?)[\'"](?:,\s*(.+?))?\)': '_directive_can',
        r'@endcan':                              '_directive_endcan',
        r'@cannot\([\'"](.+?)[\'"](?:,\s*(.+?))?\)': '_directive_cannot',
        r'@endcannot':                           '_directive_endcannot',
        r'@env\([\'"](.+?)[\'"]\)':              '_directive_env',
        r'@endenv':                              '_directive_endenv',
        r'@production':                          '_directive_production',
        r'@endproduction':                       '_directive_endproduction',
        r'@push\([\'"](.+?)[\'"]\)':             '_directive_push',
        r'@endpush':                             '_directive_endpush',
        r'@stack\([\'"](.+?)[\'"]\)':            '_directive_stack',
        r'@once':                                '_directive_once',
        r'@endonce':                             '_directive_endonce',
        r'@verbatim':                            '_directive_verbatim',
        r'@endverbatim':                         '_directive_endverbatim',
        r'@dump\((.+?)\)':                       '_directive_dump',
        r'@dd\((.+?)\)':                         '_directive_dd',
        r'@php':                                 '_directive_php',
        r'@endphp':                              '_directive_endphp',
        r'@json\((.+?)\)':                       '_directive_json',
        r'@class\((.+?)\)':                      '_directive_class',
        r'@style\((.+?)\)':                      '_directive_style',
        r'@checked\((.+?)\)':                    '_directive_checked',
        r'@selected\((.+?)\)':                   '_directive_selected',
        r'@disabled\((.+?)\)':                   '_directive_disabled',
        r'@required\((.+?)\)':                   '_directive_required',
        r'@error\([\'"](.+?)[\'"]\)':            '_directive_error',
        r'@enderror':                            '_directive_enderror',
    }

    def __init__(self, views_path: str, cache_path: str = None):
        self._views_path = views_path
        self._cache_path = cache_path or os.path.join(
            os.path.dirname(views_path), '..', '..', 'storage', 'framework', 'views'
        )
        os.makedirs(self._cache_path, exist_ok=True)

        self._sections: Dict[str, str] = {}
        self._stacks: Dict[str, List[str]] = {}
        self._layout: Optional[str] = None
        self._verbatim = False

    def render(self, template: str, data: Dict = None) -> str:
        """Render a template with the given data."""
        data = data or {}
        content = self._get_template(template)
        compiled = self._compile(content)
        return self._evaluate(compiled, data, template)

    def _get_template(self, template: str) -> str:
        """Load template file. Supports dot notation: layouts.app -> layouts/app."""
        template_file = template.replace('.', '/') + '.blade.html'
        path = os.path.join(self._views_path, template_file)

        if not os.path.exists(path):
            # Try .html extension
            path = os.path.join(self._views_path, template.replace('.', '/') + '.html')

        if not os.path.exists(path):
            raise FileNotFoundError(f"View [{template}] not found at [{path}]")

        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def _compile(self, content: str) -> str:
        """Compile BladePy directives into HTML/Python."""
        content = self._compile_comments(content)
        content = self._compile_raw_php(content)
        content = self._compile_echo(content)
        content = self._compile_raw_echo(content)
        content = self._compile_directives(content)
        return content

    def _compile_comments(self, content: str) -> str:
        """Remove BladePy comments {{-- ... --}}."""
        return re.sub(r'\{\{--.*?--\}\}', '', content, flags=re.DOTALL)

    def _compile_echo(self, content: str) -> str:
        """Compile {{ $var }} escaped output."""
        return re.sub(
            r'\{\{\s*(.+?)\s*\}\}',
            lambda m: f'{{{{ {m.group(1)} | e }}}}',
            content
        )

    def _compile_raw_echo(self, content: str) -> str:
        """Compile {!! $var !!} unescaped output."""
        return re.sub(
            r'\{!!\s*(.+?)\s*!!\}',
            lambda m: f'{{{{ {m.group(1)} | safe }}}}',
            content
        )

    def _compile_raw_php(self, content: str) -> str:
        """Handle @php ... @endphp blocks (passthrough as Jinja)."""
        return content

    def _compile_directives(self, content: str) -> str:
        """Process all @directive patterns."""
        lines = content.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]
            compiled_line = self._compile_line(line)
            result.append(compiled_line)
            i += 1

        return '\n'.join(result)

    def _compile_line(self, line: str) -> str:
        """Compile a single line."""
        # @extends
        line = re.sub(r"@extends\(['\"](.+?)['\"]\)",
                      lambda m: f'{{% extends "{m.group(1).replace(".", "/")}.blade.html" %}}', line)
        # @section('name')
        line = re.sub(r"@section\(['\"](.+?)['\"]\)",
                      lambda m: f'{{% block {m.group(1)} %}}', line)
        # @endsection / @stop
        line = re.sub(r'@endsection|@stop', '{% endblock %}', line)
        # @yield('name', 'default')
        line = re.sub(r"@yield\(['\"](.+?)['\"](?:,\s*['\"](.+?)['\"])?\)",
                      lambda m: f'{{% block {m.group(1)} %}}{m.group(2) or ""}{{% endblock %}}', line)
        # @include
        line = re.sub(r"@include\(['\"](.+?)['\"](?:,\s*(.+?))?\)",
                      lambda m: f'{{% include "{m.group(1).replace(".", "/")}.blade.html" %}}', line)
        # @if / @elseif / @else / @endif
        line = re.sub(r'@if\((.+?)\)', lambda m: f'{{% if {m.group(1)} %}}', line)
        line = re.sub(r'@elseif\((.+?)\)', lambda m: f'{{% elif {m.group(1)} %}}', line)
        line = re.sub(r'@else\b', '{% else %}', line)
        line = re.sub(r'@endif\b', '{% endif %}', line)
        # @unless
        line = re.sub(r'@unless\((.+?)\)', lambda m: f'{{% if not ({m.group(1)}) %}}', line)
        line = re.sub(r'@endunless\b', '{% endif %}', line)
        # @foreach
        line = re.sub(r'@foreach\((.+?)\s+as\s+(.+?)\)',
                      lambda m: f'{{% for {m.group(2)} in {m.group(1)} %}}', line)
        line = re.sub(r'@endforeach\b', '{% endfor %}', line)
        # @forelse
        line = re.sub(r'@forelse\((.+?)\s+as\s+(.+?)\)',
                      lambda m: f'{{% for {m.group(2)} in {m.group(1)} %}}', line)
        line = re.sub(r'@empty\b', '{% else %}', line)
        line = re.sub(r'@endforelse\b', '{% endfor %}', line)
        # @for
        line = re.sub(r'@for\((.+?)\)', lambda m: f'{{% for {m.group(1)} %}}', line)
        line = re.sub(r'@endfor\b', '{% endfor %}', line)
        # @while
        line = re.sub(r'@while\((.+?)\)', lambda m: f'{{% while {m.group(1)} %}}', line)
        line = re.sub(r'@endwhile\b', '{% endwhile %}', line)
        # @csrf
        line = re.sub(r'@csrf\b',
                      '<input type="hidden" name="_token" value="{{ csrf_token() }}">', line)
        # @method
        line = re.sub(r"@method\(['\"](.+?)['\"]\)",
                      lambda m: f'<input type="hidden" name="_method" value="{m.group(1)}">', line)
        # @auth / @guest
        line = re.sub(r'@auth\b', '{% if current_user %}', line)
        line = re.sub(r'@endauth\b', '{% endif %}', line)
        line = re.sub(r'@guest\b', '{% if not current_user %}', line)
        line = re.sub(r'@endguest\b', '{% endif %}', line)
        # @error / @enderror
        line = re.sub(r"@error\(['\"](.+?)['\"]\)",
                      lambda m: f'{{% if errors and "{m.group(1)}" in errors %}}', line)
        line = re.sub(r'@enderror\b', '{% endif %}', line)
        # @push / @endpush / @stack
        line = re.sub(r"@push\(['\"](.+?)['\"]\)",
                      lambda m: f'{{% block stack_{m.group(1)} %}}', line)
        line = re.sub(r'@endpush\b', '{% endblock %}', line)
        line = re.sub(r"@stack\(['\"](.+?)['\"]\)",
                      lambda m: f'{{% block stack_{m.group(1)} %}}{{% endblock %}}', line)
        # @json
        line = re.sub(r'@json\((.+?)\)',
                      lambda m: f'{{{{ {m.group(1)} | tojson | safe }}}}', line)
        # @class
        line = re.sub(r'@class\((.+?)\)',
                      lambda m: f'class="{{{{ bladepy_class({m.group(1)}) }}}}"', line)
        # @checked / @selected / @disabled / @required
        line = re.sub(r'@checked\((.+?)\)',
                      lambda m: f'{{{{ "checked" if ({m.group(1)}) else "" }}}}', line)
        line = re.sub(r'@selected\((.+?)\)',
                      lambda m: f'{{{{ "selected" if ({m.group(1)}) else "" }}}}', line)
        line = re.sub(r'@disabled\((.+?)\)',
                      lambda m: f'{{{{ "disabled" if ({m.group(1)}) else "" }}}}', line)
        line = re.sub(r'@required\((.+?)\)',
                      lambda m: f'{{{{ "required" if ({m.group(1)}) else "" }}}}', line)
        # @dump / @dd
        line = re.sub(r'@dump\((.+?)\)',
                      lambda m: f'<pre>{{{{ {m.group(1)} | pprint }}}}</pre>', line)
        line = re.sub(r'@dd\((.+?)\)',
                      lambda m: f'<pre>{{{{ {m.group(1)} | pprint }}}}</pre>', line)
        # @env
        line = re.sub(r"@env\(['\"](.+?)['\"]\)",
                      lambda m: f'{{% if app_env == "{m.group(1)}" %}}', line)
        line = re.sub(r'@endenv\b', '{% endif %}', line)
        return line

    def _evaluate(self, compiled: str, data: Dict, template_name: str = '') -> str:
        """Render compiled template with Jinja2."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader(self._views_path),
            autoescape=select_autoescape(['html', 'blade.html']),
        )

        # Add global helpers
        env.globals.update({
            'csrf_token': self._csrf_token,
            'current_user': self._get_current_user(),
            'app_env': os.getenv('APP_ENV', 'production'),
            'config': self._config_helper,
            'route': self._route_helper,
            'asset': self._asset_helper,
            'old': self._old_helper,
            'errors': self._get_errors(),
            'bladepy_class': self._class_helper,
        })
        env.globals.update(data)

        # Compile the template string
        template_file = template_name.replace('.', '/') + '.blade.html'
        try:
            tmpl = env.get_template(template_file)
        except Exception:
            tmpl = env.from_string(compiled)

        return tmpl.render(**data)

    def _csrf_token(self) -> str:
        from flask import session
        if '_token' not in session:
            import secrets
            session['_token'] = secrets.token_hex(32)
        return session.get('_token', '')

    def _get_current_user(self):
        try:
            from flask_login import current_user
            return current_user if current_user.is_authenticated else None
        except Exception:
            try:
                from flask import session
                return session.get('user')
            except Exception:
                return None

    def _get_errors(self):
        try:
            from flask import session
            return session.get('errors', {})
        except Exception:
            return {}

    def _config_helper(self, key: str, default=None):
        try:
            from laraflask.core.config import Config
            return default
        except Exception:
            return default

    def _route_helper(self, name: str, **params) -> str:
        try:
            from flask import url_for
            return url_for(name, **params)
        except Exception:
            return f"#{name}"

    def _asset_helper(self, path: str) -> str:
        return f"/public/{path.lstrip('/')}"

    def _old_helper(self, key: str, default: Any = None) -> Any:
        try:
            from flask import session
            old_input = session.get('_old_input', {})
            return old_input.get(key, default)
        except Exception:
            return default

    def _class_helper(self, classes: Dict) -> str:
        return ' '.join(k for k, v in classes.items() if v)


# ─── Flask Integration ────────────────────────────────────────────────────────

def make_blade_renderer(views_path: str, cache_path: str = None):
    """Create a Flask-compatible render function using BladePy."""
    engine = BladePyEngine(views_path, cache_path)

    def render_blade(template: str, **context) -> str:
        return engine.render(template, context)

    return render_blade
