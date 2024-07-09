userprofile = getenv('USERPROFILE');
data_folder = fullfile(userprofile, '.flim-labs', 'data');

% Get the recent spectroscopy file
files = dir(fullfile(data_folder, 'spectroscopy*'));
file_names = {files.name};
is_spectroscopy = cellfun(@(x) isempty(strfind(x, 'calibration')) && isempty(strfind(x, 'phasors')), file_names);
spectroscopy_files = files(is_spectroscopy);
[~, idx] = sort([spectroscopy_files.datenum], 'descend');
file_path = fullfile(data_folder, spectroscopy_files(idx(1)).name);
fprintf('Using data file: %s\n', file_path);

% Open the file
fid = fopen(file_path, 'rb');
if fid == -1
    error('Could not open file');
end

% Check for 'SP01' identifier
sp01 = fread(fid, 4, 'char');
if ~isequal(char(sp01'), 'SP01')
    fprintf('Invalid data file\n');
    fclose(fid);
    return;
end

% Read metadata
json_length = fread(fid, 1, 'uint32');
metadata_json = fread(fid, json_length, 'char');
metadata = jsondecode(char(metadata_json'));

% Print metadata information
if isfield(metadata, 'channels') && ~isempty(metadata.channels)
    enabled_channels = sprintf('Channel %d, ', metadata.channels + 1);
    fprintf('Enabled channels: %s\n', enabled_channels(1:end-2));
end
if isfield(metadata, 'bin_width_micros') && ~isempty(metadata.bin_width_micros)
    fprintf('Bin width: %dus\n', metadata.bin_width_micros);
end
if isfield(metadata, 'acquisition_time_millis') && ~isempty(metadata.acquisition_time_millis)
    fprintf('Acquisition time: %.2fs\n', metadata.acquisition_time_millis / 1000);
end
if isfield(metadata, 'laser_period_ns') && ~isempty(metadata.laser_period_ns)
    fprintf('Laser period: %dns\n', metadata.laser_period_ns);
end
if isfield(metadata, 'tau_ns') && ~isempty(metadata.tau_ns)
    fprintf('Tau: %dns\n', metadata.tau_ns);
end

num_channels = length(metadata.channels);
channel_curves = cell(1, num_channels);
for i = 1:num_channels
    channel_curves{i} = [];
end
times = [];

% Read data
while ~feof(fid)
    time_data = fread(fid, 1, 'double');
    if isempty(time_data)
        break;
    end
    times = [times; time_data / 1e9];
    
    for i = 1:num_channels
        curve_data = fread(fid, 256, 'uint32');
        if length(curve_data) < 256
            break;
        end
        channel_curves{i} = [channel_curves{i}; curve_data'];
    end
end
fclose(fid);

% Plotting
figure;
hold on;
xlabel('Bin');
ylabel('Intensity');
set(gca, 'YScale', 'log');
title(sprintf('Spectroscopy (time: %.2fs, curves stored: %d)', round(times(end)), length(times)));

total_max = -inf;
total_min = inf;
for i = 1:num_channels
    sum_curve = sum(channel_curves{i}, 1);
    total_max = max(total_max, max(sum_curve));
    total_min = min(total_min, min(sum_curve));
    plot(sum_curve, 'DisplayName', sprintf('Channel %d', metadata.channels(i) + 1));
end

ylim([total_min * 0.99, total_max * 1.01]);
legend show;
hold off;
