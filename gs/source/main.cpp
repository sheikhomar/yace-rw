// #include <cxxopts.hpp>
#include <clustering/kmeans.hpp>
#include <coresets/group_sampling.hpp>
#include <coresets/sensitivity_sampling.hpp>
#include <coresets/uniform_sampling.hpp>
#include <data/data_parser.hpp>
#include <data/csv_parser.hpp>
#include <data/census_parser.hpp>
#include <data/covertype_parser.hpp>
#include <data/tower_parser.hpp>
#include <utils/random.hpp>
#include <utils/stop_watch.hpp>
#include <blaze/Blaze.h>

using namespace std;
using namespace clustering;
using namespace data;

void writeDoneFile(const std::string &outputDir)
{
    std::string outputFilePath = outputDir + "/done.out";
    std::ofstream outData(outputFilePath, std::ifstream::out);
    outData << "done\n";
    outData.close();
}

void outputResultsToFile(const std::shared_ptr<blaze::DynamicMatrix<double>> originalDataPoints, const std::shared_ptr<coresets::Coreset> coreset, const std::string &outputDir)
{
  std::string outputFilePath = outputDir + "/results.txt.gz";

  namespace io = boost::iostreams;
  std::ofstream fileStream(outputFilePath, std::ios_base::out | std::ios_base::binary);
  io::filtering_streambuf<io::output> fos;
  fos.push(io::gzip_compressor(io::gzip_params(io::gzip::best_compression)));
  fos.push(fileStream);
  std::ostream outData(&fos);

  coreset->writeToStream(*originalDataPoints, outData);
}

int main(int argc, char **argv)
{
  if (argc < 8)
  {
    std::cout << "Usage: algorithm dataset k m seed output_path [low_data_path]" << std::endl;
    std::cout << "  algorithm     = algorithm" << std::endl;
    std::cout << "  dataset       = dataset name" << std::endl;
    std::cout << "  data_path     = file path to dataset" << std::endl;
    std::cout << "  k             = number of desired centers" << std::endl;
    std::cout << "  m             = coreset size" << std::endl;
    std::cout << "  seed          = random seed" << std::endl;
    std::cout << "  output_dir    = path to output results" << std::endl;
    std::cout << std::endl;
    std::cout << "7 arguments expected, got " << argc - 1 << ":" << std::endl;
    for (int i = 1; i < argc; ++i)
      std::cout << " " << i << ": " << argv[i] << std::endl;
    return 1;
  }

  std::string algorithmName(argv[1]);
  std::string datasetName(argv[2]);
  std::string dataFilePath(argv[3]);
  size_t k = std::stoul(argv[4]);
  size_t m = std::stoul(argv[5]);
  int randomSeed = std::stoi(argv[6]);
  std::string outputDir(argv[7]);

  boost::algorithm::to_lower(algorithmName);
  boost::algorithm::trim(algorithmName);

  boost::algorithm::to_lower(datasetName);
  boost::algorithm::trim(datasetName);

  std::cout << "Running " << algorithmName << " with following parameters:\n";
  std::cout << " - Dataset:       " << datasetName << "\n";
  std::cout << " - Input path:    " << dataFilePath << "\n";
  std::cout << " - Clusters:      " << k << "\n";
  std::cout << " - Coreset size:  " << m << "\n";
  std::cout << " - Random Seed:   " << randomSeed << "\n";
  std::cout << " - Output dir:    " << outputDir << "\n";

  std::cout << "Initializing randomess with random seed: " << randomSeed << "\n";
  utils::Random::initialize(randomSeed);
  
  std::shared_ptr<IDataParser> dataParser;
  if (datasetName == "census")
  {
    dataParser = std::make_shared<CensusParser>();
  }
  else if (datasetName == "covertype")
  {
    dataParser = std::make_shared<CovertypeParser>();
  }
  else if (datasetName == "tower")
  {
    dataParser = std::make_shared<TowerParser>();
  }
  else
  {
    std::cout << "Unknown dataset: " << datasetName << "\n";
    return -1;
  }

  std::shared_ptr<blaze::DynamicMatrix<double>> data;
  {
    utils::StopWatch timeDataParsing(true);
    std::cout << "Parsing data:" << std::endl;
    data = dataParser->parse(dataFilePath);
    std::cout << "Data parsed: " << data->rows() << " x " << data->columns() << " in "<< timeDataParsing.elapsedStr() << std::endl;
  }

  std::cout << "Begin coreset algorithm: " << algorithmName << "\n";
  std::shared_ptr<coresets::Coreset> coreset;
  utils::StopWatch timeCoresetComputation(true);

  if (algorithmName == "sensitivity-sampling")
  {
    coresets::SensitivitySampling algo(2*k, m);
    coreset = algo.run(*data);
  }
  else if (algorithmName == "uniform-sampling")
  {
    coresets::UniformSampling algo(m);
    coreset = algo.run(*data);
  }
  else if (algorithmName == "group-sampling")
  {
    size_t beta = 10000;
    size_t groupRangeSize = 4;
    size_t minimumGroupSamplingSize = 1;
    coresets::GroupSampling algo(2*k, m, beta, groupRangeSize, minimumGroupSamplingSize);
    coreset = algo.run(*data);
  }
  else 
  {
    std::cout << "Unknown algorithm: " << algorithmName << "\n";
    return -1;
  }
  
  std::cout << "Algorithm completed in " << timeCoresetComputation.elapsedStr() << std::endl;

  outputResultsToFile(data, coreset, outputDir);
  writeDoneFile(outputDir);
  return 0;
}
