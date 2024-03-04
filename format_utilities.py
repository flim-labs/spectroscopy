from math import log, floor

class FormatUtils:
    @staticmethod
    def format_size(size_in_bytes):
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0

        while size_in_bytes >= 1024 and unit_index < len(units) - 1:
            size_in_bytes /= 1024.0
            unit_index += 1
        return f"{size_in_bytes:.2f} {units[unit_index]}"

    @staticmethod
    def format_cps(number):
        if number == 0:
            return '0'
        units = ['', 'K', 'M', 'G', 'T', 'P']
        k = 1000.0
        magnitude = int(floor(log(number, k)))
        return '%.2f%s' % (number / k ** magnitude, units[magnitude])
