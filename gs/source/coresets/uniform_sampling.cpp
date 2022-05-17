#include <coresets/uniform_sampling.hpp>

using namespace coresets;

UniformSampling::UniformSampling(size_t targetSamplesInCoreset) : TargetSamplesInCoreset(targetSamplesInCoreset)
{
}

std::shared_ptr<Coreset>
UniformSampling::run(const blaze::DynamicMatrix<double> &data)
{
    auto coreset = std::make_shared<Coreset>(TargetSamplesInCoreset);

    size_t nPoints = data.rows();

    auto sampledIndices = random.choice(TargetSamplesInCoreset);

    double weight = static_cast<double>(nPoints) / static_cast<double>(TargetSamplesInCoreset);

    // Loop through the sampled points and calculate
    // the weight associated with each of these points.
    for (size_t j = 0; j < TargetSamplesInCoreset; j++)
    {
        size_t sampledPointIndex = (*sampledIndices)[j];
        coreset->addPoint(sampledPointIndex, weight);
    }

    return coreset;
}
