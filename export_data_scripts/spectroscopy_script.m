file_path = '<FILE-PATH>';
% Open the file            
fid = fopen(file_path, 'rb');
if fid == -1
    error('Could not open file');
end

% Check for 'SP01' identifier
sp01 = fread(fid, 4, 'char');
if ~isequal(char(sp01'), 'SP01')
    fprintf('Invalid data file');
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
    laser_period_ns = metadata.laser_period_ns;
    fprintf('Laser period: %dns\n', laser_period_ns);
else
    error('Laser period not found in metadata.');
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

% Calculate the x-axis values based on the laser period
num_bins = 256;
x_values = linspace(0, laser_period_ns, num_bins);

% Plotting
figure;
hold on;
xlabel(sprintf('Time (ns, Laser period = %d ns)', laser_period_ns));
ylabel('Intensity');
title(sprintf('Spectroscopy (time: %.2fs, curves stored: %d)', round(times(end)), length(times)));

total_max = -inf;
total_min = inf;
for i = 1:num_channels
    sum_curve = sum(channel_curves{i}, 1);
    total_max = max(total_max, max(sum_curve));
    total_min = min(total_min, min(sum_curve));
    plot(x_values, sum_curve, 'DisplayName', sprintf('Channel %d', metadata.channels(i) + 1));
end

ylim([total_min * 0.99, total_max * 1.01]);
xlim([0, laser_period_ns]);
legend show;
hold off;