# read data line from .clk file and return
# datetime object of the epoch
def make_dt_from_clk(instring):
    fields = instring.split()
    year = fields[2]
    month = fields[3]
    day = fields[4]
    hour = fields[5]
    minute = fields[6]
    seconds = fields[7]
    # trash is the clock offset; don't use it here
    (seconds,trash) = seconds.split('.')

    return datetime(int(year), int(month), int(day), \
        int(hour), int(minute), int(seconds))

# return unix timestamp from clock record
def make_timestamp_from_clk(instring):
    return make_dt_from_clk(instring)

# return day of year as string from .clk AR line
def make_doy_from_clk(instring):
    dt = make_dt_from_clk(instring)
    return make_doy_from_dt(dt)


# read NRCan .clk files and return dt of first epoch
def get_first_epoch_from_clk(files):
    global first_epoch
    first_epoch= datetime.min
    with open(files[0],'r') as f:
        count = 0
        for line in f:
            line = f.readline()
            if line.startswith('AR'):
                if count == 0:
                    first_epoch = make_dt_from_clk(line)
                    break
        return first_epoch

# read NRCan .clk files and return dt of last epoch
def get_final_epoch_from_clk(files):
    final_epoch = datetime.min
    with open(files[len(files)-1],'r') as f:
        for line in f:
            pass
    final_epoch = make_dt_from_clk(line)
    return final_epoch

# read NRCan .clk files and return total number of epochs
def get_epoch_count_from_clk(files):
    with open(files[0],'r') as f:
        count = 0
        for line in f:
            line = f.readline()
            if line.startswith('AR'):
                count = count + 1
        return count

# read NRCan .clk files and get tau from first two epochs in first file
def get_tau_from_clk(files):
    global tau
    tau = 0
    start = datetime.min
    this_epoch = datetime.min
    count = 0
    # only need to look at the first file
    with open(files[0],'r') as f:
        for line in f:
            if line.startswith('AR'):
                if count == 0:
                    first_epoch = make_dt_from_clk(line)
                if count == 1:
                    this_epoch = make_dt_from_clk(line)
                    tau = get_delta_seconds(this_epoch,first_epoch)
                    break
                count += 1
    return tau
