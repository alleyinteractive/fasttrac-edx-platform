from django.core.management.base import BaseCommand, CommandError
from lms.djangoapps.ccx.models import CustomCourseForEdX
from lms.djangoapps.ccx.overrides import _get_overrides_for_ccx
from openedx.core.djangoapps.content.course_structures.models import CourseStructure

from opaque_keys.edx.keys import CourseKey, UsageKey

COURSE_ID = 'course-v1:Kauffman+nv+nv'


class Command(BaseCommand):
    help = """Task for getting the number of used / not hidden modules in total."""

    def log(self, msg):
        """Log a message go STDOUT."""
        self.stdout.write(msg)

    def log_title(self, title):
        """Log a formatted title."""
        self.log('=' * 100)
        self.log(title)
        self.log('')

    def populate_data(self):
        """
        Populate a dictionary with module data (IDs and boolean if they are hidden).
        Structure:
            - course_id
            - chapters
                - chapter name
                - block_id
                - modules (course structure contains module names)
                    - name
                    - block_id
            -ccx
                - name
                - modules
                    - block_id
                    - hidden
        """
        course_key = CourseKey.from_string(COURSE_ID)
        course_structure = CourseStructure.objects.get(course_id=course_key).ordered_blocks

        data = {
            'course_id': COURSE_ID,
            'chapters': [],
            'ccx': [],
        }

        for k, block in course_structure.items():
            if block['block_type'] == 'chapter':
                chapter_id = UsageKey.from_string(k)
                modules = []
                for child in block['children']:
                    module_id = UsageKey.from_string(child)
                    modules.append({
                        'name': course_structure[child]['display_name'],
                        'block_id': module_id.block_id,
                    })
                data['chapters'].append({
                    'name': block['display_name'],
                    'block_id': chapter_id.block_id,
                    'modules': modules,
                })

        for ccx in CustomCourseForEdX.objects.all():
            overrides = _get_overrides_for_ccx(ccx)
            modules = []
            for k, v in overrides.items():
                if k.block_type == 'sequential':
                    modules.append({
                        'block_id': k.block_id,
                        'hidden': v['visible_to_staff_only']
                    })
            ccx_data = {
                'name': ccx.display_name,
                'modules': modules
            }

            data['ccx'].append(ccx_data)

        return data

    def handle(self, *args, **options):
        """Main command handler."""
        data = self.populate_data()
        self.log_title('TOTAL')

        all_ccx_modules = []
        for ccx in data['ccx']:
            all_ccx_modules.extend(ccx['modules'])

        for chapter in data['chapters']:
            self.log(chapter['name'])
            for module in chapter['modules']:
                visible = 0
                for ccx_module in all_ccx_modules:
                    if ccx_module['block_id'] == module['block_id'] and not ccx_module['hidden']:
                        visible += 1
                self.log('{}: {}'.format(module['name'], visible))
            self.log('')
